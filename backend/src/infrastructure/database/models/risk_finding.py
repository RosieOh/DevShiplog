from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from infrastructure.database.session import Base


class RiskCategory(str, enum.Enum):
    TOKEN = "token"
    EMAIL = "email"
    PHONE = "phone"
    INTERNAL_URL = "internal_url"
    COMPANY = "company"
    SECRET = "secret"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MASKED = "masked"
    DELETED = "deleted"
    IGNORED = "ignored"


class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_version_id = Column(String(36), ForeignKey("draft_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(RiskCategory), nullable=False)
    severity = Column(Enum(RiskSeverity), default=RiskSeverity.MED)
    snippet = Column(Text)
    location_json = Column(JSON)  # line range, column 등
    status = Column(Enum(RiskStatus), default=RiskStatus.OPEN, index=True)
    ignore_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    draft_version = relationship("DraftVersion", back_populates="risk_findings")

