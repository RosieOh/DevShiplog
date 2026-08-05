from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from src.infrastructure.database.session import Base


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

    __table_args__ = (
        # 예약 실행 워커가 "지금 보내야 할 것" 을 뽑는 경로.
        # scheduled_at 단독 인덱스로는 status 필터가 걸리지 않는다.
        Index("ix_schedules_status_time", "status", "scheduled_at"),
    )

