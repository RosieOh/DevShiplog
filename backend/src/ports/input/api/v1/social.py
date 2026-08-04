"""좋아요 / 댓글 / 팔로우 / 알림 / 신고 (인증 필요)."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.application.use_cases.moderation.report import ReportContentUseCase, ToggleBlockUseCase
from src.application.use_cases.social.interactions import (
    CreateCommentUseCase,
    ModifyCommentUseCase,
    ToggleFollowUseCase,
    ToggleLikeUseCase,
)
from src.ports.input.api.v1.dependencies import (
    client_identity,
    enforce_rate_limit,
    get_block_repo,
    get_comment_repo,
    get_current_user_id,
    get_current_user_id_sse,
    get_follow_repo,
    get_like_repo,
    get_notification_repo,
    get_post_repo,
    get_report_repo,
    get_user_repo,
)
from src.infrastructure.database.repositories.social_repository_impl import (
    NotificationRepositoryImpl,
)
from src.infrastructure.database.session import SessionLocal
from src.ports.output.repositories.moderation_repository import BlockRepository, ReportRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.social_repository import (
    CommentRepository,
    FollowRepository,
    LikeRepository,
    NotificationRepository,
)
from src.infrastructure.external import revalidation
from src.ports.output.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter()

# 알림 스트림. 폴링보다 촘촘하되 DB 를 때리는 간격은 넉넉히 둔다.
NOTIFY_POLL_SECONDS = 3.0
NOTIFY_HEARTBEAT_SECONDS = 20.0
# 연결을 영원히 붙잡지 않는다. 끊기면 EventSource 가 알아서 다시 붙는다.
NOTIFY_STREAM_MAX_SECONDS = 900.0


def _sse(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class CommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    parent_id: Optional[str] = None


class ReportRequest(BaseModel):
    target_type: str  # post | comment | user
    target_id: str
    reason: str  # spam | abuse | sensitive | copyright | other
    detail: str = Field(default="", max_length=500)


# ------------------------------------------------------------------ 좋아요


@router.post("/posts/{post_id}/like")
def toggle_like(
    request: Request,
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    like_repo: LikeRepository = Depends(get_like_repo),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
):
    enforce_rate_limit("like", client_identity(request, user_id))
    return ToggleLikeUseCase(post_repo, like_repo, notification_repo).execute(user_id, post_id)


# -------------------------------------------------------------------- 댓글


@router.post("/posts/{post_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    request: Request,
    post_id: str,
    payload: CommentRequest,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    block_repo: BlockRepository = Depends(get_block_repo),
):
    enforce_rate_limit("comment", client_identity(request, user_id))
    use_case = CreateCommentUseCase(post_repo, comment_repo, notification_repo, block_repo)
    result = use_case.execute(user_id, post_id, payload.body, payload.parent_id)

    post = post_repo.get_by_id(post_id)
    if post and post.user:
        background.add_task(
            revalidation.notify, revalidation.tags_for_post(post.user.handle, post.slug)
        )
    return {"id": result["id"]}


@router.put("/comments/{comment_id}")
def update_comment(
    comment_id: str,
    payload: CommentRequest,
    user_id: str = Depends(get_current_user_id),
    comment_repo: CommentRepository = Depends(get_comment_repo),
    post_repo: PostRepository = Depends(get_post_repo),
):
    return ModifyCommentUseCase(comment_repo, post_repo).update(user_id, comment_id, payload.body)


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: str,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    comment_repo: CommentRepository = Depends(get_comment_repo),
    post_repo: PostRepository = Depends(get_post_repo),
):
    comment = comment_repo.get_by_id(comment_id)
    post = post_repo.get_by_id(comment.post_id) if comment else None
    result = ModifyCommentUseCase(comment_repo, post_repo).delete(user_id, comment_id)

    if post and post.user:
        background.add_task(
            revalidation.notify, revalidation.tags_for_post(post.user.handle, post.slug)
        )
    return result


# ------------------------------------------------------------------ 팔로우


@router.post("/users/{handle}/follow")
def toggle_follow(
    request: Request,
    handle: str,
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
    follow_repo: FollowRepository = Depends(get_follow_repo),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
):
    enforce_rate_limit("follow", client_identity(request, user_id))
    return ToggleFollowUseCase(user_repo, follow_repo, notification_repo).execute(user_id, handle)


@router.get("/feed/following")
def following_feed(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
):
    """내가 팔로우한 사람들의 최신 글."""
    posts = post_repo.list_following_feed(user_id, limit=limit + 1, offset=offset)
    return {
        "items": [
            {
                "id": p.id,
                "slug": p.slug,
                "title": p.title,
                "summary": p.summary,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "like_count": p.like_count,
                "comment_count": p.comment_count,
                "author": {
                    "handle": p.user.handle,
                    "display_name": p.user.display_name or p.user.handle,
                    "avatar_url": p.user.avatar_url,
                },
                "url": f"/@{p.user.handle}/{p.slug}",
            }
            for p in posts[:limit]
        ],
        "has_more": len(posts) > limit,
    }


# -------------------------------------------------------------------- 알림


@router.get("/notifications")
def list_notifications(
    limit: int = Query(30, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
):
    items = notification_repo.list_for_user(user_id, limit, offset)
    return {
        "unread_count": notification_repo.unread_count(user_id),
        "items": [
            {
                "id": n.id,
                "type": n.type.value,
                "actor": {
                    "handle": n.actor.handle,
                    "display_name": n.actor.display_name or n.actor.handle,
                    "avatar_url": n.actor.avatar_url,
                },
                "post": (
                    {"title": n.post.title, "url": f"/@{n.post.user.handle}/{n.post.slug}"}
                    if n.post and n.post.user and n.post.user.handle
                    else None
                ),
                "read": n.read_at is not None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


@router.get("/notifications/stream")
async def stream_notifications(
    user_id: str = Depends(get_current_user_id_sse),
):
    """읽지 않은 알림 수를 밀어준다.

    폴링을 대신한다. 알림은 대부분의 시간 동안 아무 일도 없는데, 그때도
    30초마다 요청이 오면 접속자 수에 비례해 그냥 버려지는 쿼리가 쌓인다.

    보내는 값은 개수뿐이다. 목록까지 스트림에 실으면 읽음 처리·페이지네이션과
    상태가 갈라진다. 개수가 바뀌면 클라이언트가 목록을 다시 가져오면 된다.
    """

    async def event_generator():
        db = SessionLocal()
        try:
            repo = NotificationRepositoryImpl(db)
            last: Optional[int] = None
            elapsed = 0.0
            since_heartbeat = 0.0

            while elapsed < NOTIFY_STREAM_MAX_SECONDS:
                # MySQL 의 REPEATABLE READ 는 트랜잭션이 시작된 시점의 스냅샷을 계속 본다.
                # 새로 시작하지 않으면 다른 세션이 넣은 알림이 영원히 안 보인다.
                db.rollback()
                count = repo.unread_count(user_id)
                if count != last:
                    last = count
                    since_heartbeat = 0.0
                    yield _sse({"type": "unread", "count": count})

                await asyncio.sleep(NOTIFY_POLL_SECONDS)
                elapsed += NOTIFY_POLL_SECONDS
                since_heartbeat += NOTIFY_POLL_SECONDS

                if since_heartbeat >= NOTIFY_HEARTBEAT_SECONDS:
                    since_heartbeat = 0.0
                    # 프록시가 유휴 연결을 끊지 않도록 주석 라인을 흘린다.
                    yield ": keep-alive\n\n"

            # 상한에 닿으면 그냥 끊는다. EventSource 가 알아서 다시 붙는다.
        except asyncio.CancelledError:  # 클라이언트가 연결을 끊음
            raise
        except Exception:
            logger.exception("알림 스트림 오류 (user=%s)", user_id)
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
        },
    )


@router.post("/notifications/read")
def mark_notifications_read(
    ids: Optional[List[str]] = None,
    user_id: str = Depends(get_current_user_id),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
):
    return {"updated": notification_repo.mark_read(user_id, ids)}


# ---------------------------------------------------------- 신고 / 차단


@router.post("/reports", status_code=status.HTTP_201_CREATED)
def report_content(
    request: Request,
    payload: ReportRequest,
    user_id: str = Depends(get_current_user_id),
    report_repo: ReportRepository = Depends(get_report_repo),
    post_repo: PostRepository = Depends(get_post_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    enforce_rate_limit("report", client_identity(request, user_id))
    use_case = ReportContentUseCase(report_repo, post_repo, comment_repo, user_repo)
    return use_case.execute(
        user_id, payload.target_type, payload.target_id, payload.reason, payload.detail
    )


@router.post("/users/{handle}/block")
def toggle_block(
    handle: str,
    user_id: str = Depends(get_current_user_id),
    block_repo: BlockRepository = Depends(get_block_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    return ToggleBlockUseCase(block_repo, user_repo).execute(user_id, handle)
