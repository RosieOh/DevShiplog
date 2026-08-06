from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import PostStatus
from src.infrastructure.database.session import Base

__all__ = ["Post", "PostStatus"]


class Post(Base):
    """공개 발행물.

    Draft 는 계속 자동저장되는 작업본이고, Post 는 발행 시점의 스냅샷이다.
    한 테이블로 합치면 편집 중 저장이 공개된 글을 실시간으로 바꿔버리고
    캐시 무효화 시점도 잡을 수 없다.
    """

    __tablename__ = "posts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # 어느 작업본에서 나왔는지. 작업본이 지워져도 발행물은 남는다.
    draft_id = Column(String(36), ForeignKey("drafts.id", ondelete="SET NULL"), nullable=True)

    slug = Column(String(120), nullable=False)
    title = Column(String(300), nullable=False)
    content_md = Column(Text, nullable=False)
    summary = Column(String(300))
    cover_url = Column(String(1000))

    status = Column(Enum(PostStatus), nullable=False, default=PostStatus.PUBLISHED, index=True)
    published_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 마지막으로 "지금도 동작한다" 고 작성자가 확인한 시각.
    #
    # published_at 과 다른 개념이다. 작성일은 글이 맞는지와 상관이 없다 —
    # 2년 전 글도 어제 다시 돌려봤다면 믿을 수 있다.
    verified_at = Column(DateTime, index=True)

    # 정렬·표시에 매번 COUNT 를 돌리지 않기 위한 비정규화 카운터
    like_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    view_count = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="posts")
    draft = relationship("Draft")
    tags = relationship("PostTag", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    series_links = relationship("SeriesPost", back_populates="post", cascade="all, delete-orphan")
    stacks = relationship(
        "PostStack", back_populates="post", cascade="all, delete-orphan",
        order_by="PostStack.position",
    )
    signals = relationship("PostSignal", back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        # 공개 URL 은 /@handle/slug 이므로 사용자 안에서만 유일하면 된다.
        UniqueConstraint("user_id", "slug", name="unique_post_slug_per_user"),
        # 블로그 홈: 이 사람의 공개글을 최신순으로
        Index("ix_posts_user_status_published", "user_id", "status", "published_at"),
        # 전체 피드: 공개글 최신순 / 인기순
        Index("ix_posts_status_published", "status", "published_at"),
        Index("ix_posts_status_likes", "status", "like_count"),
    )
