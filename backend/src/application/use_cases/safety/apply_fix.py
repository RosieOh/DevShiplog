from typing import Any, Dict, Optional

from src.application.errors import NotFoundError, ValidationError
from src.domain.enums import RiskStatus, SafetyAction
from src.domain.services.safety_scanner import SafetyScanner
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.risk_finding_repository import RiskFindingRepository


class ApplyFixUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        risk_finding_repo: RiskFindingRepository,
    ):
        self.draft_repo = draft_repo
        self.risk_finding_repo = risk_finding_repo
        self.scanner = SafetyScanner()

    def execute(
        self,
        user_id: str,
        draft_id: str,
        finding_id: str,
        action: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Safety 검사 결과에 대한 조치를 적용한다."""
        try:
            safety_action = SafetyAction(action)
        except ValueError:
            raise ValidationError(f"지원하지 않는 조치입니다: {action}") from None

        draft = self.draft_repo.get_by_id(draft_id)
        if not draft:
            raise NotFoundError("Draft 를 찾을 수 없습니다.")
        # 소유권 불일치도 404 로 답한다. 403 은 "그 Draft 는 존재한다" 를 알려주는 셈이라
        # guards.get_owned_draft 와 동작이 달라지고 존재 여부가 새어나간다.
        if draft.user_id != user_id:
            raise NotFoundError("Draft 를 찾을 수 없습니다.")

        latest_version = self.draft_repo.get_latest_version(draft_id)
        if not latest_version:
            raise NotFoundError("Draft 버전이 없습니다.")

        finding = self.risk_finding_repo.get_by_id(finding_id)
        if not finding:
            raise NotFoundError("검사 결과를 찾을 수 없습니다.")
        # finding 이 이 Draft 의 최신 버전에 속하는지 확인 (다른 글의 finding_id 차단)
        if finding.draft_version_id != latest_version.id:
            raise NotFoundError("검사 결과를 찾을 수 없습니다.")

        if safety_action is SafetyAction.IGNORE:
            self.risk_finding_repo.update_status(
                finding_id=finding_id, status=RiskStatus.IGNORED, ignore_reason=reason
            )
            return {"message": "무시 처리했습니다.", "new_version_no": None}

        payload = {"snippet": finding.snippet, "location": finding.location_json}
        content = latest_version.content_md or ""

        if safety_action is SafetyAction.MASK:
            new_content = self.scanner.mask_content(content, payload)
            new_status = RiskStatus.MASKED
        else:  # DELETE — 줄 전체가 아니라 해당 값만 제거한다.
            new_content = self.scanner.remove_finding(content, payload)
            new_status = RiskStatus.DELETED

        if new_content == content:
            raise ValidationError(
                "본문이 변경되어 해당 위치를 찾을 수 없습니다. 다시 검사해주세요."
            )

        version_no = self.draft_repo.next_version_no(draft_id)
        new_version = self.draft_repo.create_version(
            draft_id=draft_id,
            version_no=version_no,
            content_md=new_content,
            meta_json=latest_version.meta_json,
        )
        self.risk_finding_repo.update_status(finding_id=finding_id, status=new_status)

        return {"message": "조치를 적용했습니다.", "new_version_no": new_version.version_no}
