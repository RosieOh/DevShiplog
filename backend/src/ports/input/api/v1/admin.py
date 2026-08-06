"""운영자 화면용 API.

신고는 쌓이는데 처리할 사람이 없으면 신고 기능은 장식이다.
공개 서비스로 열기 전에 반드시 있어야 한다.
"""

from datetime import timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.application.errors import NotFoundError, ValidationError
from src.domain.enums import PostStatus, ReportStatus
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
    # 신고가 타당하면 글을 내린다. 사용자 정지는 아직 없다 —
    # 그건 되돌리기가 훨씬 어렵고, 지금 규모에서 필요하지 않다.
    unpublish_post: bool = False


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
    if payload.unpublish_post and report.target_type.value == "post":
        post = post_repo.get_by_id(report.target_id)
        if post and post.status is PostStatus.PUBLISHED:
            post_repo.set_status(post.id, PostStatus.UNLISTED)
            unpublished = True

    return {"status": report.status.value, "unpublished": unpublished}


@router.get("/summary")
def admin_summary(
    _: str = Depends(get_admin_user_id),
    report_repo: ReportRepository = Depends(get_report_repo),
):
    """운영자가 첫 화면에서 볼 것.

    지금은 "밀린 신고가 몇 건인가" 하나뿐이다. 대시보드를 크게 만드는 것보다
    처리해야 할 일이 눈에 띄는 게 먼저다.
    """
    pending = report_repo.list_open(limit=100, offset=0)
    return {"pending_reports": len(pending)}
