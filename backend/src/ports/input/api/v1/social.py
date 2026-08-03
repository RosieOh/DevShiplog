"""좋아요 / 댓글 / 팔로우 / 알림 / 신고 (인증 필요)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
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
    get_follow_repo,
    get_like_repo,
    get_notification_repo,
    get_post_repo,
    get_report_repo,
    get_user_repo,
)
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

router = APIRouter()


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
