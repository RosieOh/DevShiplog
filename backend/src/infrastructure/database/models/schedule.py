from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from infrastructure.database.session import Base


class ScheduleStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    draft_id = Column(String(36), ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50))  # wordpress, notion, medium
    scheduled_at = Column(DateTime, nullable=False, index=True)
    status = Column(Enum(ScheduleStatus), default=ScheduleStatus.PENDING)
    error_text = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="schedules")
    draft = relationship("Draft", back_populates="schedules")

