from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.application.use_cases.safety.apply_fix import ApplyFixUseCase
from src.application.use_cases.safety.scan_draft import ScanDraftUseCase
from src.ports.input.api.v1.dependencies import (
    get_current_user_id,
    get_draft_repo,
    get_risk_finding_repo,
)
from src.ports.input.api.v1.guards import get_owned_draft
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.risk_finding_repository import RiskFindingRepository

router = APIRouter()


class RiskFindingResponse(BaseModel):
    id: str
    category: str
    severity: str
    snippet: str
    location: dict
    status: str


class ScanResponse(BaseModel):
    findings: List[RiskFindingResponse]
    count: int


class ApplyFixRequest(BaseModel):
    finding_id: str
    action: str  # mask, delete, ignore
    reason: Optional[str] = None


class ApplyFixResponse(BaseModel):
    message: str
    new_version_no: Optional[int] = None


@router.post("/drafts/{draft_id}/scan", response_model=ScanResponse)
def scan_draft(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    risk_finding_repo: RiskFindingRepository = Depends(get_risk_finding_repo),
):
    """Safety 검사 실행"""
    use_case = ScanDraftUseCase(draft_repo, risk_finding_repo)
    findings = use_case.execute(user_id, draft_id)
    return {"findings": findings, "count": len(findings)}


@router.get("/drafts/{draft_id}/findings", response_model=List[RiskFindingResponse])
def get_findings(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    risk_finding_repo: RiskFindingRepository = Depends(get_risk_finding_repo),
) -> List[Dict[str, Any]]:
    """Safety 검사 결과 조회"""
    get_owned_draft(draft_repo, draft_id, user_id)

    latest_version = draft_repo.get_latest_version(draft_id)
    if not latest_version:
        return []

    return [
        {
            "id": f.id,
            "category": f.category.value,
            "severity": f.severity.value,
            "snippet": f.snippet,
            "location": f.location_json,
            "status": f.status.value,
        }
        for f in risk_finding_repo.get_by_draft_version_id(latest_version.id)
    ]


@router.post("/drafts/{draft_id}/apply", response_model=ApplyFixResponse)
def apply_fix(
    draft_id: str,
    request: ApplyFixRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    risk_finding_repo: RiskFindingRepository = Depends(get_risk_finding_repo),
):
    """Safety 검사 결과 적용 (마스킹/삭제/무시)"""
    use_case = ApplyFixUseCase(draft_repo, risk_finding_repo)
    return use_case.execute(user_id, draft_id, request.finding_id, request.action, request.reason)
