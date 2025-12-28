from typing import List
from sqlalchemy.orm import Session
from infrastructure.database.models.risk_finding import RiskFinding, RiskCategory, RiskSeverity, RiskStatus
from ports.output.repositories.risk_finding_repository import RiskFindingRepository
import uuid


class RiskFindingRepositoryImpl(RiskFindingRepository):
    def __init__(self, db: Session):
        self.db = db

    async def create(
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

    async def get_by_draft_version_id(self, draft_version_id: str) -> List[RiskFinding]:
        return (
            self.db.query(RiskFinding)
            .filter(RiskFinding.draft_version_id == draft_version_id)
            .all()
        )

    async def update_status(
        self,
        finding_id: str,
        status: RiskStatus,
        ignore_reason: str = None,
    ) -> RiskFinding:
        finding = self.db.query(RiskFinding).filter(RiskFinding.id == finding_id).first()
        if not finding:
            raise ValueError(f"RiskFinding {finding_id} not found")
        
        finding.status = status
        if ignore_reason:
            finding.ignore_reason = ignore_reason
        
        self.db.commit()
        self.db.refresh(finding)
        return finding

