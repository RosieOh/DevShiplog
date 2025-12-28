from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, JSON, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from infrastructure.database.session import Base


class JobType(str, enum.Enum):
    EXTRACT = "extract"
    STYLE = "style"
    DRAFT = "draft"
    TRANSFORM = "transform"
    SAFETY = "safety"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, index=True)
    progress = Column(Integer, default=0)
    current_step = Column(String(50))  # ingest, outline, draft, style, safety, polish
    steps = Column(JSON)  # 단계별 진행률 정보
    result_ref = Column(JSON)  # 결과 참조 (draft_id 등)
    error_text = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="jobs")
    usage_logs = relationship("UsageLog", back_populates="job", cascade="all, delete-orphan")

