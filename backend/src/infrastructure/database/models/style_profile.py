from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from infrastructure.database.session import Base


class StyleProfileStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blog_url = Column(String(500), nullable=False)
    sample_count = Column(Integer, default=5)
    status = Column(Enum(StyleProfileStatus), default=StyleProfileStatus.QUEUED)
    profile_json = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="style_profiles")
    drafts = relationship("Draft", back_populates="style_profile")

