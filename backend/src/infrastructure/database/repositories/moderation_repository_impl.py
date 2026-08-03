import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.domain.enums import ReportReason, ReportStatus, ReportTargetType
from src.infrastructure.database.models.moderation import Report, UserBlock
from src.ports.output.repositories.moderation_repository import BlockRepository, ReportRepository


class ReportRepositoryImpl(ReportRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        reporter_id: str,
        target_type: ReportTargetType,
        target_id: str,
        reason: ReportReason,
        detail: str = "",
    ) -> Optional[Report]:
        report = Report(
            id=str(uuid.uuid4()),
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            detail=detail or None,
        )
        self.db.add(report)
        try:
            self.db.commit()
        except IntegrityError:
            # 같은 사람이 같은 대상을 다시 신고. 조용히 무시한다.
            self.db.rollback()
            return None
        self.db.refresh(report)
        return report

    def count_open_for_target(self, target_type: ReportTargetType, target_id: str) -> int:
        return (
            self.db.query(func.count(Report.id))
            .filter(
                Report.target_type == target_type,
                Report.target_id == target_id,
                Report.status == ReportStatus.OPEN,
            )
            .scalar()
            or 0
        )

    def list_open(self, limit: int, offset: int) -> List[Report]:
        return (
            self.db.query(Report)
            .options(joinedload(Report.reporter))
            .filter(Report.status == ReportStatus.OPEN)
            .order_by(Report.created_at.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def resolve(self, report_id: str, status: ReportStatus) -> Report:
        report = self.db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")
        report.status = status
        report.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        self.db.refresh(report)
        return report


class BlockRepositoryImpl(BlockRepository):
    def __init__(self, db: Session):
        self.db = db

    def block(self, blocker_id: str, blocked_id: str) -> bool:
        if blocker_id == blocked_id or self.is_blocked(blocker_id, blocked_id):
            return False
        self.db.add(UserBlock(blocker_id=blocker_id, blocked_id=blocked_id))
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return False
        return True

    def unblock(self, blocker_id: str, blocked_id: str) -> bool:
        deleted = (
            self.db.query(UserBlock)
            .filter(UserBlock.blocker_id == blocker_id, UserBlock.blocked_id == blocked_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return bool(deleted)

    def blocked_ids(self, blocker_id: str) -> List[str]:
        return [
            r[0]
            for r in self.db.query(UserBlock.blocked_id)
            .filter(UserBlock.blocker_id == blocker_id)
            .all()
        ]

    def is_blocked(self, blocker_id: str, blocked_id: str) -> bool:
        return (
            self.db.query(UserBlock.blocker_id)
            .filter(UserBlock.blocker_id == blocker_id, UserBlock.blocked_id == blocked_id)
            .first()
            is not None
        )
