"""좋아요 / 팔로우 / 댓글.

각 동작은 알림을 함께 만든다. 알림 생성 실패가 본 동작을 되돌리면 안 되므로
저장소 쪽에서 자기 자신에 대한 알림을 걸러내고, 여기서는 흐름만 조립한다.
"""

from typing import Any, Dict, List, Optional

from src.application.errors import NotFoundError, PermissionDeniedError, ValidationError
from src.domain.enums import NotificationType, PostStatus
from src.ports.output.repositories.moderation_repository import BlockRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.social_repository import (
    CommentRepository,
    FollowRepository,
    LikeRepository,
    NotificationRepository,
)
from src.ports.output.repositories.user_repository import UserRepository

MAX_COMMENT_LEN = 1000


def _visible(post) -> bool:
    return post is not None and post.status is PostStatus.PUBLISHED


class ToggleLikeUseCase:
    def __init__(
        self,
        post_repo: PostRepository,
        like_repo: LikeRepository,
        notification_repo: NotificationRepository,
    ):
        self.post_repo = post_repo
        self.like_repo = like_repo
        self.notification_repo = notification_repo

    def execute(self, user_id: str, post_id: str) -> Dict[str, Any]:
        post = self.post_repo.get_by_id(post_id)
        if not _visible(post):
            raise NotFoundError("글을 찾을 수 없습니다.")

        if self.like_repo.exists(post_id, user_id):
            self.like_repo.remove(post_id, user_id)
            liked = False
        else:
            self.like_repo.add(post_id, user_id)
            liked = True
            self.notification_repo.create(
                user_id=post.user_id,
                actor_id=user_id,
                notification_type=NotificationType.LIKE,
                post_id=post_id,
            )

        refreshed = self.post_repo.get_by_id(post_id)
        return {"liked": liked, "like_count": refreshed.like_count}


class ToggleFollowUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        follow_repo: FollowRepository,
        notification_repo: NotificationRepository,
    ):
        self.user_repo = user_repo
        self.follow_repo = follow_repo
        self.notification_repo = notification_repo

    def execute(self, user_id: str, handle: str) -> Dict[str, Any]:
        target = self.user_repo.get_by_handle(handle)
        if not target:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        if target.id == user_id:
            raise ValidationError("자기 자신은 팔로우할 수 없습니다.")

        if self.follow_repo.exists(user_id, target.id):
            self.follow_repo.unfollow(user_id, target.id)
            following = False
        else:
            self.follow_repo.follow(user_id, target.id)
            following = True
            self.notification_repo.create(
                user_id=target.id,
                actor_id=user_id,
                notification_type=NotificationType.FOLLOW,
            )

        refreshed = self.user_repo.get_by_id(target.id)
        return {"following": following, "follower_count": refreshed.follower_count}


class CreateCommentUseCase:
    def __init__(
        self,
        post_repo: PostRepository,
        comment_repo: CommentRepository,
        notification_repo: NotificationRepository,
        block_repo: BlockRepository,
    ):
        self.post_repo = post_repo
        self.comment_repo = comment_repo
        self.notification_repo = notification_repo
        self.block_repo = block_repo

    def execute(
        self, user_id: str, post_id: str, body: str, parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        body = (body or "").strip()
        if not body:
            raise ValidationError("댓글 내용을 입력해주세요.")
        if len(body) > MAX_COMMENT_LEN:
            raise ValidationError(f"댓글은 {MAX_COMMENT_LEN}자를 넘을 수 없습니다.")

        post = self.post_repo.get_by_id(post_id)
        if not _visible(post):
            raise NotFoundError("글을 찾을 수 없습니다.")

        # 글쓴이가 나를 차단했다면 댓글을 달 수 없다.
        if self.block_repo.is_blocked(post.user_id, user_id):
            raise PermissionDeniedError("이 글에는 댓글을 달 수 없습니다.")

        parent = None
        if parent_id:
            parent = self.comment_repo.get_by_id(parent_id)
            if not parent or parent.post_id != post_id:
                raise NotFoundError("원 댓글을 찾을 수 없습니다.")
            if parent.parent_id:
                # 답글의 답글은 허용하지 않는다. 모바일에서 읽히지 않는다.
                raise ValidationError("답글에는 다시 답글을 달 수 없습니다.")

        comment = self.comment_repo.create(post_id, user_id, body, parent_id)

        if parent is not None:
            self.notification_repo.create(
                user_id=parent.user_id,
                actor_id=user_id,
                notification_type=NotificationType.REPLY,
                post_id=post_id,
                comment_id=comment.id,
            )
        self.notification_repo.create(
            user_id=post.user_id,
            actor_id=user_id,
            notification_type=NotificationType.COMMENT,
            post_id=post_id,
            comment_id=comment.id,
        )

        return {"id": comment.id, "created_at": comment.created_at}


class ModifyCommentUseCase:
    def __init__(self, comment_repo: CommentRepository, post_repo: PostRepository):
        self.comment_repo = comment_repo
        self.post_repo = post_repo

    def update(self, user_id: str, comment_id: str, body: str) -> Dict[str, Any]:
        comment = self._owned(user_id, comment_id)
        body = (body or "").strip()
        if not body:
            raise ValidationError("댓글 내용을 입력해주세요.")
        if len(body) > MAX_COMMENT_LEN:
            raise ValidationError(f"댓글은 {MAX_COMMENT_LEN}자를 넘을 수 없습니다.")
        updated = self.comment_repo.update_body(comment_id, body)
        return {"id": updated.id, "body": updated.body}

    def delete(self, user_id: str, comment_id: str) -> Dict[str, Any]:
        comment = self.comment_repo.get_by_id(comment_id)
        if not comment or comment.deleted_at is not None:
            raise NotFoundError("댓글을 찾을 수 없습니다.")

        # 글쓴이도 자기 글의 댓글을 지울 수 있어야 한다.
        post = self.post_repo.get_by_id(comment.post_id)
        if comment.user_id != user_id and (not post or post.user_id != user_id):
            raise NotFoundError("댓글을 찾을 수 없습니다.")

        self.comment_repo.soft_delete(comment_id)
        return {"deleted": True}

    def _owned(self, user_id: str, comment_id: str):
        comment = self.comment_repo.get_by_id(comment_id)
        if not comment or comment.user_id != user_id or comment.deleted_at is not None:
            raise NotFoundError("댓글을 찾을 수 없습니다.")
        return comment
