from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import RiskCategory, RiskSeverity, RiskStatus
from src.infrastructure.database.session import Base

__all__ = ["RiskFinding", "RiskCategory", "RiskSeverity", "RiskStatus"]


class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_version_id = Column(
        String(36), ForeignKey("draft_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(Enum(RiskCategory), nullable=False)
    severity = Column(Enum(RiskSeverity), default=RiskSeverity.MED)
    snippet = Column(Text)
    location_json = Column(JSON)  # line range, column 등
    status = Column(Enum(RiskStatus), default=RiskStatus.OPEN, index=True)
    ignore_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    draft_version = relationship("DraftVersion", back_populates="risk_findings")
