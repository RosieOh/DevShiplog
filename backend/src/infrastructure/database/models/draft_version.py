from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from infrastructure.database.session import Base


class DraftVersion(Base):
    __tablename__ = "draft_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_id = Column(String(36), ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    content_md = Column(Text)  # 마크다운 내용
    content_ref = Column(String(500))  # S3 key (큰 내용)
    meta_json = Column(JSON)  # title, tags, summary 등
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    draft = relationship("Draft", back_populates="versions")
    risk_findings = relationship("RiskFinding", back_populates="draft_version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("draft_id", "version_no", name="unique_draft_version"),
    )

