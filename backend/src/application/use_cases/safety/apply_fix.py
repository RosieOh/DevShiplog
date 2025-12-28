from typing import Dict, Any
from ports.output.repositories.draft_repository import DraftRepository
from ports.output.repositories.risk_finding_repository import RiskFindingRepository
from infrastructure.database.models.risk_finding import RiskStatus
from domain.services.safety_scanner import SafetyScanner


class ApplyFixUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        risk_finding_repo: RiskFindingRepository,
    ):
        self.draft_repo = draft_repo
        self.risk_finding_repo = risk_finding_repo
        self.scanner = SafetyScanner()

    async def execute(
        self,
        draft_id: str,
        finding_id: str,
        action: str,
        reason: str = None,
    ) -> Dict[str, Any]:
        """Safety 검사 결과 적용"""
        draft = await self.draft_repo.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        latest_version = await self.draft_repo.get_latest_version(draft_id)
        if not latest_version:
            raise ValueError(f"No version found for draft {draft_id}")

        # Finding 조회
        findings = await self.risk_finding_repo.get_by_draft_version_id(latest_version.id)
        finding = next((f for f in findings if f.id == finding_id), None)
        if not finding:
            raise ValueError(f"Finding {finding_id} not found")

        # 액션 처리
        if action == "mask":
            # 마스킹 적용
            content = latest_version.content_md or ""
            masked_content = self.scanner.mask_content(content, {
                "snippet": finding.snippet,
                "location": finding.location_json,
            })
            
            # 새 버전 생성
            version_no = latest_version.version_no + 1
            await self.draft_repo.create_version(
                draft_id=draft_id,
                version_no=version_no,
                content_md=masked_content,
                meta_json=latest_version.meta_json,
            )

            await self.risk_finding_repo.update_status(
                finding_id=finding_id,
                status=RiskStatus.MASKED,
            )

        elif action == "delete":
            # 삭제 (해당 부분 제거)
            content = latest_version.content_md or ""
            lines = content.split("\n")
            location = finding.location_json
            if location.get("line") and location["line"] <= len(lines):
                lines.pop(location["line"] - 1)
            
            new_content = "\n".join(lines)
            version_no = latest_version.version_no + 1
            await self.draft_repo.create_version(
                draft_id=draft_id,
                version_no=version_no,
                content_md=new_content,
                meta_json=latest_version.meta_json,
            )

            await self.risk_finding_repo.update_status(
                finding_id=finding_id,
                status=RiskStatus.DELETED,
            )

        elif action == "ignore":
            await self.risk_finding_repo.update_status(
                finding_id=finding_id,
                status=RiskStatus.IGNORED,
                ignore_reason=reason,
            )

        return {"message": "Fix applied successfully"}

