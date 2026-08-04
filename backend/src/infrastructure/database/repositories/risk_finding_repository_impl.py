import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.enums import RiskCategory, RiskSeverity, RiskStatus
from src.infrastructure.database.models.risk_finding import RiskFinding
from src.ports.output.repositories.risk_finding_repository import RiskFindingRepository


class RiskFindingRepositoryImpl(RiskFindingRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        draft_version_id: str,
        category: str,
        severity: str,
        snippet: str,
        location_json: dict,
    ) -> RiskFinding:
        finding = RiskFinding(
            id=str(uuid.uuid4()),
            draft_version_id=draft_version_id,
            category=RiskCategory(category),
            severity=RiskSeverity(severity),
            snippet=snippet,
            location_json=location_json,
            status=RiskStatus.OPEN,
        )
        self.db.add(finding)
        self.db.commit()
        self.db.refresh(finding)
        return finding

    def get_by_id(self, finding_id: str) -> Optional[RiskFinding]:
        return self.db.query(RiskFinding).filter(RiskFinding.id == finding_id).first()

    def get_by_draft_version_id(self, draft_version_id: str) -> List[RiskFinding]:
        return (
            self.db.query(RiskFinding)
            .filter(RiskFinding.draft_version_id == draft_version_id)
            .order_by(RiskFinding.severity.desc())
            .all()
        )

    def delete_by_draft_version_id(self, draft_version_id: str) -> int:
        deleted = (
            self.db.query(RiskFinding)
            .filter(RiskFinding.draft_version_id == draft_version_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted

    def update_status(
        self,
        finding_id: str,
        status: RiskStatus,
        ignore_reason: Optional[str] = None,
    ) -> RiskFinding:
        finding = self.get_by_id(finding_id)
        if not finding:
            raise ValueError(f"RiskFinding {finding_id} not found")

        finding.status = status
        if ignore_reason is not None:
            finding.ignore_reason = ignore_reason

        self.db.commit()
        self.db.refresh(finding)
        return finding
