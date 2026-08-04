from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Numeric, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from src.infrastructure.database.session import Base


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    model_name = Column(String(100))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    cost_usd = Column(Numeric(10, 6))
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="usage_logs")
    job = relationship("Job", back_populates="usage_logs")

