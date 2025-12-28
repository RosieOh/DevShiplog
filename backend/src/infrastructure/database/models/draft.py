from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from infrastructure.database.session import Base


class DraftStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50))  # troubleshooting, implementation, etc.
    audience = Column(String(50))  # junior, intermediate, etc.
    length_preset = Column(String(50))  # short, default, long
    style_profile_id = Column(String(36), ForeignKey("style_profiles.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(DraftStatus), default=DraftStatus.ACTIVE)
    tags = Column(JSON)  # ["tag1", "tag2"]
    notes = Column(Text)  # 사용자 메모
    checklist = Column(JSON)  # [{"id": "1", "text": "...", "checked": false}]
    generation_log = Column(JSON)  # 생성 히스토리
    outline = Column(JSON)  # 목차 정보
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="drafts")
    style_profile = relationship("StyleProfile", back_populates="drafts")
    versions = relationship("DraftVersion", back_populates="draft", cascade="all, delete-orphan", order_by="DraftVersion.version_no")
    schedules = relationship("Schedule", back_populates="draft", cascade="all, delete-orphan")

