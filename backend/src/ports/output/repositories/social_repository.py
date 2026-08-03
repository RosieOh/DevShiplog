from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Sequence

if TYPE_CHECKING:
    from src.infrastructure.database.models.social import Comment, Notification
    from src.infrastructure.database.models.user import User


class CommentRepository(ABC):
    @abstractmethod
    def create(
        self, post_id: str, user_id: str, body: str, parent_id: Optional[str] = None
    ) -> "Comment":
        ...

    @abstractmethod
    def get_by_id(self, comment_id: str) -> Optional["Comment"]:
        ...

    @abstractmethod
    def list_for_post(self, post_id: str, exclude_user_ids: Sequence[str] = ()) -> List["Comment"]:
        """루트 댓글 + 답글을 한 번에 가져온다 (N+1 방지)."""
        ...

    @abstractmethod
    def update_body(self, comment_id: str, body: str) -> "Comment":
        ...

    @abstractmethod
    def soft_delete(self, comment_id: str) -> "Comment":
        """답글이 달린 댓글을 실제로 지우면 흐름이 끊기므로 자리만 남긴다."""
        ...

    @abstractmethod
    def count_for_post(self, post_id: str) -> int:
        ...


class LikeRepository(ABC):
    @abstractmethod
    def add(self, post_id: str, user_id: str) -> bool:
        """이미 눌렀으면 False."""
        ...

    @abstractmethod
    def remove(self, post_id: str, user_id: str) -> bool:
        ...

    @abstractmethod
    def exists(self, post_id: str, user_id: str) -> bool:
        ...

    @abstractmethod
    def liked_post_ids(self, user_id: str, post_ids: Sequence[str]) -> set:
        """목록 화면에서 좋아요 여부를 한 번에 조회한다."""
        ...


class FollowRepository(ABC):
    @abstractmethod
    def follow(self, follower_id: str, following_id: str) -> bool:
        ...

    @abstractmethod
    def unfollow(self, follower_id: str, following_id: str) -> bool:
        ...

    @abstractmethod
    def exists(self, follower_id: str, following_id: str) -> bool:
        ...

    @abstractmethod
    def following_ids(self, user_id: str) -> List[str]:
        ...

    @abstractmethod
    def list_followers(self, user_id: str, limit: int, offset: int) -> List["User"]:
        ...

    @abstractmethod
    def list_following(self, user_id: str, limit: int, offset: int) -> List["User"]:
        ...


class NotificationRepository(ABC):
    @abstractmethod
    def create(
        self,
        user_id: str,
        actor_id: str,
        notification_type,
        post_id: Optional[str] = None,
        comment_id: Optional[str] = None,
    ) -> Optional["Notification"]:
        """자기 자신이 일으킨 알림은 만들지 않는다 (None 반환)."""
        ...

    @abstractmethod
    def list_for_user(self, user_id: str, limit: int, offset: int) -> List["Notification"]:
        ...

    @abstractmethod
    def unread_count(self, user_id: str) -> int:
        ...

    @abstractmethod
    def mark_read(self, user_id: str, notification_ids: Optional[Sequence[str]] = None) -> int:
        """id 를 주지 않으면 전체 읽음 처리."""
        ...
