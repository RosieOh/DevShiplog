from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.infrastructure.database.session import Base

__all__ = ["Series", "SeriesPost"]


class Series(Base):
    """연재 묶음. 여러 편으로 이어지는 글을 순서대로 보여준다."""

    __tablename__ = "series"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    slug = Column(String(120), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="series")
    posts = relationship(
        "SeriesPost",
        back_populates="series",
        cascade="all, delete-orphan",
        order_by="SeriesPost.position",
    )

    __table_args__ = (UniqueConstraint("user_id", "slug", name="unique_series_slug_per_user"),)


class SeriesPost(Base):
    __tablename__ = "series_posts"

    series_id = Column(
        String(36), ForeignKey("series.id", ondelete="CASCADE"), primary_key=True
    )
    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    position = Column(Integer, nullable=False, default=0)

    series = relationship("Series", back_populates="posts")
    post = relationship("Post", back_populates="series_links")
