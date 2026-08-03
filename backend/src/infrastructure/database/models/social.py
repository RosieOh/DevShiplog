"""소셜 상호작용: 댓글 / 좋아요 / 팔로우 / 알림.

카운터(like_count 등)는 Post 에 비정규화해 두고, 여기 행 수와 함께 갱신한다.
목록 정렬에서 매번 COUNT 를 도는 것이 가장 먼저 느려지는 지점이기 때문이다.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import NotificationType
from src.infrastructure.database.session import Base

__all__ = ["Comment", "PostLike", "Follow", "Notification"]


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # 1단계 답글만 허용한다 (Velog 와 동일). 무한 중첩은 모바일에서 읽히지 않는다.
    parent_id = Column(String(36), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)

    body = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    # 대댓글이 달린 댓글을 실제로 지우면 흐름이 끊긴다. 소프트 삭제로 자리를 남긴다.
    deleted_at = Column(DateTime, nullable=True)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    replies = relationship(
        "Comment", back_populates="parent", cascade="all, delete-orphan", single_parent=True
    )
    parent = relationship("Comment", back_populates="replies", remote_side=[id])

    __table_args__ = (Index("ix_comments_post_created", "post_id", "created_at"),)


class PostLike(Base):
    __tablename__ = "post_likes"

    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())

    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")

    __table_args__ = (UniqueConstraint("post_id", "user_id", name="unique_post_like"),)


class Follow(Base):
    __tablename__ = "follows"

    follower_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    following_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = Column(DateTime, server_default=func.now())

    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="unique_follow"),
        # 자기 자신을 팔로우하는 행을 DB 차원에서 막는다.
        CheckConstraint("follower_id <> following_id", name="no_self_follow"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 알림을 받는 사람
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # 알림을 일으킨 사람
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)

    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    comment_id = Column(String(36), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)

    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor = relationship("User", foreign_keys=[actor_id])
    post = relationship("Post")
    comment = relationship("Comment")

    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)
