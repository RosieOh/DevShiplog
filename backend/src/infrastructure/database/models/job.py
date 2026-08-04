from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import JobStatus, JobType
from src.infrastructure.database.session import Base

__all__ = ["Job", "JobStatus", "JobType"]


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, index=True)
    progress = Column(Integer, default=0)
    result_ref = Column(JSON)  # 결과 참조 (draft_id 등)
    error_text = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="jobs")
    usage_logs = relationship("UsageLog", back_populates="job", cascade="all, delete-orphan")
