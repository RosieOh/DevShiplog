from typing import Any, Dict, List

from src.application.errors import NotFoundError, PermissionDeniedError
from src.domain.services.safety_scanner import SafetyScanner
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.risk_finding_repository import RiskFindingRepository


class ScanDraftUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        risk_finding_repo: RiskFindingRepository,
    ):
        self.draft_repo = draft_repo
        self.risk_finding_repo = risk_finding_repo
        self.scanner = SafetyScanner()

    def execute(self, user_id: str, draft_id: str) -> List[Dict[str, Any]]:
        """최신 버전 본문에 대해 Safety 검사를 수행한다."""
        draft = self.draft_repo.get_by_id(draft_id)
        if not draft:
            raise NotFoundError("Draft 를 찾을 수 없습니다.")
        if draft.user_id != user_id:
            raise PermissionDeniedError("이 Draft 에 접근할 수 없습니다.")

        latest_version = self.draft_repo.get_latest_version(draft_id)
        if not latest_version:
            return []

        # 재스캔 시 이전 결과가 쌓이지 않도록 먼저 정리한다.
        self.risk_finding_repo.delete_by_draft_version_id(latest_version.id)

        results = []
        for finding in self.scanner.scan(latest_version.content_md or ""):
            saved = self.risk_finding_repo.create(
                draft_version_id=latest_version.id,
                category=finding["category"],
                severity=finding["severity"],
                snippet=finding["snippet"],
                location_json=finding["location"],
            )
            results.append(
                {
                    "id": saved.id,
                    "category": saved.category.value,
                    "severity": saved.severity.value,
                    "snippet": saved.snippet,
                    "location": saved.location_json,
                    "status": saved.status.value,
                }
            )

        return results
