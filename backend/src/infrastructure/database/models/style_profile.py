from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import StyleProfileStatus
from src.infrastructure.database.session import Base

__all__ = ["StyleProfile", "StyleProfileStatus"]


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blog_url = Column(String(500), nullable=False)
    sample_count = Column(Integer, default=5)
    status = Column(Enum(StyleProfileStatus), default=StyleProfileStatus.QUEUED)
    profile_json = Column(JSON)
    error_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="style_profiles")
    drafts = relationship("Draft", back_populates="style_profile")
    # 이 문체를 기본값으로 쓰는 템플릿들.
    # 문체를 지워도 템플릿은 남는다(문체 없이도 쓸 수 있다) — cascade 를 걸지 않는다.
    templates = relationship("Template", back_populates="style_profile")
