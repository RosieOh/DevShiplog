import uuid
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.domain.enums import NotificationType
from src.infrastructure.database.models.post import Post
from src.infrastructure.database.models.social import Comment, Follow, Notification, PostLike
from src.infrastructure.database.models.user import User
from src.ports.output.repositories.social_repository import (
    CommentRepository,
    FollowRepository,
    LikeRepository,
    NotificationRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _decrement(column):
    """카운터를 1 줄이되 0 아래로 내려가지 않게 한다.

    GREATEST() 는 MariaDB 전용이라 테스트가 도는 SQLite 에서 깨진다.
    CASE 는 두 방언 모두에서 동작한다.
    """
    return case((column > 0, column - 1), else_=0)


class CommentRepositoryImpl(CommentRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, post_id: str, user_id: str, body: str, parent_id: Optional[str] = None
    ) -> Comment:
        comment = Comment(
            id=str(uuid.uuid4()),
            post_id=post_id,
            user_id=user_id,
            parent_id=parent_id,
            body=body,
        )
        self.db.add(comment)
        # 카운터는 삭제되지 않은 댓글만 센다.
        self.db.query(Post).filter(Post.id == post_id).update(
            {Post.comment_count: Post.comment_count + 1}, synchronize_session=False
        )
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_by_id(self, comment_id: str) -> Optional[Comment]:
        return self.db.query(Comment).filter(Comment.id == comment_id).first()

    def list_for_post(self, post_id: str, exclude_user_ids: Sequence[str] = ()) -> List[Comment]:
        q = (
            self.db.query(Comment)
            .options(joinedload(Comment.user))
            .filter(Comment.post_id == post_id)
        )
        if exclude_user_ids:
            q = q.filter(~Comment.user_id.in_(list(exclude_user_ids)))
        return q.order_by(Comment.created_at.asc()).all()

    def update_body(self, comment_id: str, body: str) -> Comment:
        comment = self.get_by_id(comment_id)
        if not comment:
            raise ValueError(f"Comment {comment_id} not found")
        comment.body = body
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def soft_delete(self, comment_id: str) -> Comment:
        comment = self.get_by_id(comment_id)
        if not comment:
            raise ValueError(f"Comment {comment_id} not found")
        if comment.deleted_at is None:
            comment.deleted_at = _now()
            self.db.query(Post).filter(Post.id == comment.post_id).update(
                {Post.comment_count: _decrement(Post.comment_count)},
                synchronize_session=False,
            )
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def count_for_post(self, post_id: str) -> int:
        return (
            self.db.query(func.count(Comment.id))
            .filter(Comment.post_id == post_id, Comment.deleted_at.is_(None))
            .scalar()
            or 0
        )


class LikeRepositoryImpl(LikeRepository):
    def __init__(self, db: Session):
        self.db = db

    def add(self, post_id: str, user_id: str) -> bool:
        if self.exists(post_id, user_id):
            return False
        self.db.add(PostLike(post_id=post_id, user_id=user_id))
        self.db.query(Post).filter(Post.id == post_id).update(
            {Post.like_count: Post.like_count + 1}, synchronize_session=False
        )
        try:
            self.db.commit()
        except IntegrityError:
            # 동시에 두 번 눌린 경우. 유니크 제약이 최종 방어선이다.
            self.db.rollback()
            return False
        return True

    def remove(self, post_id: str, user_id: str) -> bool:
        deleted = (
            self.db.query(PostLike)
            .filter(PostLike.post_id == post_id, PostLike.user_id == user_id)
            .delete(synchronize_session=False)
        )
        if deleted:
            self.db.query(Post).filter(Post.id == post_id).update(
                {Post.like_count: _decrement(Post.like_count)},
                synchronize_session=False,
            )
        self.db.commit()
        return bool(deleted)

    def exists(self, post_id: str, user_id: str) -> bool:
        return (
            self.db.query(PostLike.post_id)
            .filter(PostLike.post_id == post_id, PostLike.user_id == user_id)
            .first()
            is not None
        )

    def liked_post_ids(self, user_id: str, post_ids: Sequence[str]) -> set:
        if not post_ids:
            return set()
        rows = (
            self.db.query(PostLike.post_id)
            .filter(PostLike.user_id == user_id, PostLike.post_id.in_(list(post_ids)))
            .all()
        )
        return {r[0] for r in rows}


class FollowRepositoryImpl(FollowRepository):
    def __init__(self, db: Session):
        self.db = db

    def follow(self, follower_id: str, following_id: str) -> bool:
        if follower_id == following_id or self.exists(follower_id, following_id):
            return False
        self.db.add(Follow(follower_id=follower_id, following_id=following_id))
        self.db.query(User).filter(User.id == following_id).update(
            {User.follower_count: User.follower_count + 1}, synchronize_session=False
        )
        self.db.query(User).filter(User.id == follower_id).update(
            {User.following_count: User.following_count + 1}, synchronize_session=False
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return False
        return True

    def unfollow(self, follower_id: str, following_id: str) -> bool:
        deleted = (
            self.db.query(Follow)
            .filter(Follow.follower_id == follower_id, Follow.following_id == following_id)
            .delete(synchronize_session=False)
        )
        if deleted:
            self.db.query(User).filter(User.id == following_id).update(
                {User.follower_count: _decrement(User.follower_count)},
                synchronize_session=False,
            )
            self.db.query(User).filter(User.id == follower_id).update(
                {User.following_count: _decrement(User.following_count)},
                synchronize_session=False,
            )
        self.db.commit()
        return bool(deleted)

    def exists(self, follower_id: str, following_id: str) -> bool:
        return (
            self.db.query(Follow.follower_id)
            .filter(Follow.follower_id == follower_id, Follow.following_id == following_id)
            .first()
            is not None
        )

    def following_ids(self, user_id: str) -> List[str]:
        return [
            r[0]
            for r in self.db.query(Follow.following_id)
            .filter(Follow.follower_id == user_id)
            .all()
        ]

    def list_followers(self, user_id: str, limit: int, offset: int) -> List[User]:
        return (
            self.db.query(User)
            .join(Follow, Follow.follower_id == User.id)
            .filter(Follow.following_id == user_id)
            .order_by(Follow.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def list_following(self, user_id: str, limit: int, offset: int) -> List[User]:
        return (
            self.db.query(User)
            .join(Follow, Follow.following_id == User.id)
            .filter(Follow.follower_id == user_id)
            .order_by(Follow.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )


class NotificationRepositoryImpl(NotificationRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: str,
        actor_id: str,
        notification_type: NotificationType,
        post_id: Optional[str] = None,
        comment_id: Optional[str] = None,
    ) -> Optional[Notification]:
        # 내 글에 내가 댓글을 달았다고 알림이 오면 안 된다.
        if user_id == actor_id:
            return None

        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            actor_id=actor_id,
            type=notification_type,
            post_id=post_id,
            comment_id=comment_id,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list_for_user(self, user_id: str, limit: int, offset: int) -> List[Notification]:
        return (
            self.db.query(Notification)
            .options(joinedload(Notification.actor), joinedload(Notification.post))
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def unread_count(self, user_id: str) -> int:
        return (
            self.db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.read_at.is_(None))
            .scalar()
            or 0
        )

    def mark_read(self, user_id: str, notification_ids: Optional[Sequence[str]] = None) -> int:
        q = self.db.query(Notification).filter(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
        if notification_ids:
            q = q.filter(Notification.id.in_(list(notification_ids)))
        updated = q.update({Notification.read_at: _now()}, synchronize_session=False)
        self.db.commit()
        return updated
