from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import DraftStatus
from src.infrastructure.database.session import Base

__all__ = ["Draft", "DraftStatus"]


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50))  # troubleshooting, implementation, etc.
    audience = Column(String(50))  # junior, intermediate, etc.
    length_preset = Column(String(50))  # short, default, long
    style_profile_id = Column(String(36), ForeignKey("style_profiles.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(DraftStatus), default=DraftStatus.ACTIVE)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="drafts")
    style_profile = relationship("StyleProfile", back_populates="drafts")
    versions = relationship(
        "DraftVersion",
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="DraftVersion.version_no",
    )
