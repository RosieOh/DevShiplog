from typing import List, Dict, Any
from ports.output.repositories.draft_repository import DraftRepository
from ports.output.repositories.risk_finding_repository import RiskFindingRepository
from domain.services.safety_scanner import SafetyScanner


class ScanDraftUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        risk_finding_repo: RiskFindingRepository,
    ):
        self.draft_repo = draft_repo
        self.risk_finding_repo = risk_finding_repo
        self.scanner = SafetyScanner()

    async def execute(self, draft_id: str) -> List[Dict[str, Any]]:
        """Draft Safety 검사"""
        draft = await self.draft_repo.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        latest_version = await self.draft_repo.get_latest_version(draft_id)
        if not latest_version:
            return []

        # Safety 스캔
        findings = self.scanner.scan(latest_version.content_md or "")

        # DB에 저장
        risk_findings = []
        for finding in findings:
            risk_finding = await self.risk_finding_repo.create(
                draft_version_id=latest_version.id,
                category=finding["category"],
                severity=finding["severity"],
                snippet=finding["snippet"],
                location_json=finding["location"],
            )
            risk_findings.append({
                "id": risk_finding.id,
                "category": risk_finding.category.value,
                "severity": risk_finding.severity.value,
                "snippet": risk_finding.snippet,
                "location": risk_finding.location_json,
                "status": risk_finding.status.value,
            })

        return risk_findings

