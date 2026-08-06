from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import UserRole
from src.infrastructure.database.session import Base

__all__ = ["User"]


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    password_hash = Column(String(255), nullable=False)

    # --- 블로그 신원 -------------------------------------------------------
    # 공개 주소가 /@handle 이므로 이 값이 곧 블로그 URL 이다.
    # 가입 직후에는 비어 있고, 첫 발행 전에 정하도록 유도한다.
    handle = Column(String(30), unique=True, index=True, nullable=True)
    display_name = Column(String(60))
    bio = Column(Text)
    avatar_url = Column(String(1000))

    # 목록에서 매번 COUNT 하지 않기 위한 비정규화 카운터
    post_count = Column(Integer, nullable=False, default=0)
    follower_count = Column(Integer, nullable=False, default=0)
    following_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, server_default=func.now())

    # --- 글쓰기 도구 쪽 ----------------------------------------------------
    style_profiles = relationship(
        "StyleProfile", back_populates="user", cascade="all, delete-orphan"
    )
    sources = relationship("Source", back_populates="user", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    # 운영자 여부.
    #
    # 신고는 쌓이는데 처리할 사람이 없으면 신고 기능은 장식이다.
    # 별도 테이블로 빼지 않는다 — 역할이 둘뿐이고 사용자당 하나다.
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER, server_default="USER")

    templates = relationship("Template", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")

    # --- 블로그 플랫폼 쪽 --------------------------------------------------
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    series = relationship("Series", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="user", cascade="all, delete-orphan")
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    followers = relationship(
        "Follow",
        foreign_keys="Follow.following_id",
        back_populates="following",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
