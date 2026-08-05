from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import DraftStatus
from src.infrastructure.database.session import Base

__all__ = ["Draft", "DraftStatus"]


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50))  # troubleshooting, implementation, etc.
    audience = Column(String(50))  # junior, intermediate, etc.
    length_preset = Column(String(50))  # short, default, long
    style_profile_id = Column(String(36), ForeignKey("style_profiles.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(DraftStatus), default=DraftStatus.ACTIVE)
    # 작성 보조용 메모. 발행물(Post)에는 넘어가지 않는다 — 작업 중에만 쓰는 값이다.
    tags = Column(JSON)  # ["tag1", "tag2"]
    notes = Column(Text)
    checklist = Column(JSON)  # [{"id": "1", "text": "...", "checked": false}]
    generation_log = Column(JSON)  # 생성 히스토리
    outline = Column(JSON)  # 목차 정보
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="drafts")
    style_profile = relationship("StyleProfile", back_populates="drafts")
    versions = relationship(
        "DraftVersion",
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="DraftVersion.version_no",
    )
    # 예약 발행. 초안이 사라지면 예약도 의미가 없다.
    schedules = relationship("Schedule", back_populates="draft", cascade="all, delete-orphan")
