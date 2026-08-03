from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import SourceType
from src.infrastructure.database.session import Base

__all__ = ["Source", "SourceType"]


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(SourceType), nullable=False)
    origin = Column(String(500))  # 원본 URL 또는 "raw_text"
    title = Column(String(500))
    content = Column(Text)  # 작은 텍스트는 직접 저장
    content_ref = Column(String(500))  # S3 key (큰 텍스트)
    extracted_json = Column(JSON)  # headings, codeBlocks, images 등
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sources")
