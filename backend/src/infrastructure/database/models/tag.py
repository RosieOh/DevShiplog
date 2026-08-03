from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.infrastructure.database.session import Base

__all__ = ["Tag", "PostTag"]


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 정규화된 표기(소문자). 대소문자만 다른 태그가 갈라지지 않도록 한다.
    name = Column(String(40), nullable=False, unique=True, index=True)
    # 사용자가 처음 입력한 표기. 화면에는 이쪽을 보여준다.
    display_name = Column(String(40), nullable=False)
    post_count = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, server_default=func.now())

    posts = relationship("PostTag", back_populates="tag", cascade="all, delete-orphan")


class PostTag(Base):
    __tablename__ = "post_tags"

    post_id = Column(
        String(36), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    post = relationship("Post", back_populates="tags")
    tag = relationship("Tag", back_populates="posts")

    __table_args__ = (UniqueConstraint("post_id", "tag_id", name="unique_post_tag"),)
