"""신고 / 차단.

공개 댓글이 열리는 순간 스팸과 어뷰징은 들어온다.
소셜 기능과 같은 시점에 있어야 하는 장치이지 나중에 붙이는 기능이 아니다.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.domain.enums import ReportReason, ReportStatus, ReportTargetType
from src.infrastructure.database.session import Base

__all__ = ["Report", "UserBlock"]


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    target_type = Column(Enum(ReportTargetType), nullable=False)
    # 대상 종류가 여러 개라 FK 를 걸지 않는다. 삭제된 대상의 신고 이력도 남겨야 한다.
    target_id = Column(String(36), nullable=False)

    reason = Column(Enum(ReportReason), nullable=False)
    detail = Column(Text)
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.OPEN, index=True)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    reporter = relationship("User")

    __table_args__ = (
        # 같은 사람이 같은 대상을 반복 신고해 큐를 채우지 못하게 한다.
        UniqueConstraint("reporter_id", "target_type", "target_id", name="unique_report"),
        Index("ix_reports_target", "target_type", "target_id"),
    )


class UserBlock(Base):
    """차단. 차단한 사람의 댓글과 글이 내 화면에서 사라진다."""

    __tablename__ = "user_blocks"

    blocker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("blocker_id <> blocked_id", name="no_self_block"),
    )
