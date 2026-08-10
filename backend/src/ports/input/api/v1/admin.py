"""운영자 화면용 API.

신고는 쌓이는데 처리할 사람이 없으면 신고 기능은 장식이다.
공개 서비스로 열기 전에 반드시 있어야 한다.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.application.errors import NotFoundError, ValidationError
from sqlalchemy.orm import Session

from src.domain.enums import PostStatus, ReportStatus, UserRole
from src.infrastructure.config.settings import settings
from src.infrastructure.database.session import get_db
from src.infrastructure.observability import errors as error_store
from src.infrastructure.observability.health import readiness
from src.ports.input.api.v1.dependencies import (
    get_admin_user_id,
    get_post_repo,
    get_report_repo,
    get_user_repo,
)
from src.ports.output.repositories.moderation_repository import ReportRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.user_repository import UserRepository

router = APIRouter()


class ResolveRequest(BaseModel):
    # resolved = 신고가 타당했다, rejected = 문제 없었다
    status: str = Field(pattern="^(resolved|rejected)$")
    # 신고가 타당하면 글을 내린다.
    unpublish_post: bool = False
    # 반복되는 경우 작성자를 일정 기간 정지한다. 0 이면 정지하지 않는다.
    # 한 화면에서 끝내야 한다 — 신고를 처리하고 다시 사용자를 찾아 들어가야 하면
    # 그 단계에서 그만두게 된다.
    suspend_author_days: int = Field(default=0, ge=0, le=365)


def _iso_utc(value) -> Optional[str]:
    """시각을 UTC 표시가 붙은 ISO 문자열로.

    DB 에는 UTC 를 시간대 없이 저장한다. 그대로 내보내면 브라우저가 그것을
    **현지 시각**으로 읽는다 — 방금 들어온 신고가 "9시간 전" 으로 보였다.
    운영자가 처리 순서를 정하는 화면에서 시간이 틀리면 화면 자체가 쓸모없다.
    """
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _report_payload(report, post_repo: PostRepository, user_repo: UserRepository) -> Dict[str, Any]:
    """신고 한 건을 판단할 수 있을 만큼만 펼친다.

    대상 내용을 함께 싣는다. 운영자가 신고를 보고 다시 대상을 찾아 들어가야 하면
    처리가 느려지고, 느려지면 안 하게 된다.
    """
    target: Optional[Dict[str, Any]] = None
    if report.target_type.value == "post":
        post = post_repo.get_by_id(report.target_id)
        if post:
            author = post.user
            target = {
                "kind": "post",
                "title": post.title,
                "status": post.status.value,
                "excerpt": (post.content_md or "")[:280],
                "url": (
                    f"/@{author.handle}/{post.slug}" if author and author.handle else None
                ),
                "author": author.handle if author else None,
            }
    elif report.target_type.value == "user":
        user = user_repo.get_by_id(report.target_id)
        if user:
            target = {"kind": "user", "handle": user.handle, "display_name": user.display_name}

    return {
        "id": report.id,
        "reason": report.reason.value,
        "detail": report.detail or "",
        "target_type": report.target_type.value,
        "target_id": report.target_id,
        "target": target,
        "created_at": _iso_utc(report.created_at),
    }


@router.get("/reports")
def open_reports(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: str = Depends(get_admin_user_id),
    report_repo: ReportRepository = Depends(get_report_repo),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """처리 대기 중인 신고."""
    reports = report_repo.list_open(limit=limit, offset=offset)
    return {"items": [_report_payload(r, post_repo, user_repo) for r in reports]}


@router.post("/reports/{report_id}/resolve")
def resolve_report(
    report_id: str,
    payload: ResolveRequest,
    _: str = Depends(get_admin_user_id),
    report_repo: ReportRepository = Depends(get_report_repo),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    db: Session = Depends(get_db),
):
    """신고를 처리한다."""
    try:
        new_status = ReportStatus(payload.status)
    except ValueError as exc:
        raise ValidationError("알 수 없는 처리 상태입니다.") from exc

    # 저장소는 없는 신고에 ValueError 를 낸다. 그대로 두면 500 이 나가고,
    # 이미 처리된 신고를 두 번 누른 운영자에게 "서버 오류" 를 보여주게 된다.
    try:
        report = report_repo.resolve(report_id, new_status)
    except ValueError as exc:
        raise NotFoundError("신고를 찾을 수 없습니다.") from exc

    unpublished = False
    author = None
    if report.target_type.value == "post":
        post = post_repo.get_by_id(report.target_id)
        if post:
            author = post.user
            if payload.unpublish_post and post.status is PostStatus.PUBLISHED:
                post_repo.set_status(post.id, PostStatus.UNLISTED)
                unpublished = True
    elif report.target_type.value == "user":
        author = user_repo.get_by_id(report.target_id)

    suspended_until = None
    if payload.suspend_author_days and author and author.role is not UserRole.ADMIN:
        until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=payload.suspend_author_days
        )
        author.suspended_until = until
        author.suspend_reason = f"신고 처리 ({report.reason.value})"
        db.commit()
        suspended_until = _iso_utc(until)

    return {
        "status": report.status.value,
        "unpublished": unpublished,
        "suspended_until": suspended_until,
    }


class SuspendRequest(BaseModel):
    # 기한제만 둔다. 영구 정지는 오판했을 때 고칠 방법이 없고, 오판은 한다.
    # 필요하면 다시 걸면 된다.
    days: int = Field(ge=1, le=365)
    reason: str = Field(default="", max_length=300)


@router.post("/users/{handle}/suspend")
def suspend_user(
    handle: str,
    payload: SuspendRequest,
    admin_id: str = Depends(get_admin_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
    db: Session = Depends(get_db),
):
    """일정 기간 쓰기를 막는다. 읽기는 막지 않는다.

    정지된 사람도 자기 글과 정지 사유는 볼 수 있어야 한다 —
    안 그러면 무슨 일이 일어났는지 알 방법이 없고, 그건 처벌이 아니라 방치다.
    """
    user = user_repo.get_by_handle(handle)
    if not user:
        raise NotFoundError("사용자를 찾을 수 없습니다.")
    if user.id == admin_id:
        # 자기 발등을 찍으면 풀어 줄 사람이 없다.
        raise ValidationError("자기 자신은 정지할 수 없습니다.")
    if user.role is UserRole.ADMIN:
        raise ValidationError("운영자는 정지할 수 없습니다. 먼저 권한을 회수하세요.")

    until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=payload.days)
    user.suspended_until = until
    user.suspend_reason = payload.reason or None
    db.commit()

    return {
        "handle": user.handle,
        "suspended_until": _iso_utc(until),
        "reason": user.suspend_reason or "",
    }


@router.post("/users/{handle}/unsuspend")
def unsuspend_user(
    handle: str,
    _: str = Depends(get_admin_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
    db: Session = Depends(get_db),
):
    """정지 해제. 오판이었다면 바로 되돌릴 수 있어야 한다."""
    user = user_repo.get_by_handle(handle)
    if not user:
        raise NotFoundError("사용자를 찾을 수 없습니다.")
    user.suspended_until = None
    user.suspend_reason = None
    db.commit()
    return {"handle": user.handle, "suspended_until": None}


@router.get("/users/suspended")
def suspended_users(
    _: str = Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    """지금 정지 중인 사람.

    걸어 놓고 잊는 것을 막는다. 기한이 지난 것은 저절로 풀리므로 보여주지 않는다.
    """
    from src.infrastructure.database.models.user import User

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = (
        db.query(User)
        .filter(User.suspended_until.isnot(None), User.suspended_until > now)
        .order_by(User.suspended_until.asc())
        .limit(100)
        .all()
    )
    return {
        "items": [
            {
                "handle": user.handle,
                "display_name": user.display_name,
                "suspended_until": _iso_utc(user.suspended_until),
                "reason": user.suspend_reason or "",
            }
            for user in rows
        ]
    }


@router.get("/summary")
def admin_summary(
    _: str = Depends(get_admin_user_id),
    report_repo: ReportRepository = Depends(get_report_repo),
    db: Session = Depends(get_db),
):
    """운영자가 첫 화면에서 볼 것.

    처리할 신고와 최근 오류. 대시보드를 크게 만드는 것보다
    "지금 손댈 일이 있는가" 가 한눈에 보이는 게 먼저다.
    """
    pending = report_repo.list_open(limit=100, offset=0)
    return {"pending_reports": len(pending), **error_store.stored_summary(db)}


@router.get("/errors")
def recent_errors(
    limit: int = Query(20, ge=1, le=50),
    include_resolved: bool = Query(False),
    _: str = Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    """최근 서버 오류.

    DB 에서 읽는다. 예전에는 프로세스 메모리에만 있어서 재시작하면 사라지고
    워커가 여럿이면 일부만 보였다 — "어제 밤에 뭐가 터졌지" 를 물을 수 없었다.
    """
    items = error_store.stored_recent(db, limit=limit, include_resolved=include_resolved)
    return {
        "items": items,
        **error_store.stored_summary(db),
        "alerting": bool(settings.ALERT_EMAIL or settings.ALERT_WEBHOOK_URL),
    }


@router.post("/errors/{fingerprint}/resolve")
def resolve_error(
    fingerprint: str,
    _: str = Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    """확인 처리. 지우지 않는다 — 다시 나면 목록에 되돌아와야 재발을 안다."""
    if not error_store.mark_resolved(db, fingerprint):
        raise NotFoundError("그런 오류 기록이 없습니다.")
    return {"resolved": True}


@router.get("/readiness")
def admin_readiness(_: str = Depends(get_admin_user_id)):
    """의존성 상태.

    /health/ready 와 같은 점검이지만, 운영자 화면에서 보려고 여기에도 둔다.
    공개 엔드포인트는 로드밸런서가 쓰고, 이건 사람이 본다.
    """
    return readiness()
