from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from ports.input.api.v1.dependencies import get_draft_repo, get_risk_finding_repo
from ports.output.repositories.draft_repository import DraftRepository
from ports.output.repositories.risk_finding_repository import RiskFindingRepository
from application.use_cases.safety.scan_draft import ScanDraftUseCase
from application.use_cases.safety.apply_fix import ApplyFixUseCase

router = APIRouter()


class RiskFindingResponse(BaseModel):
    id: str
    category: str
    severity: str
    snippet: str
    location: dict
    status: str


class ApplyFixRequest(BaseModel):
    finding_id: str
    action: str  # mask, delete, ignore
    reason: Optional[str] = None


@router.post("/drafts/{draft_id}/scan")
async def scan_draft(
    draft_id: str,
    draft_repo: DraftRepository = Depends(get_draft_repo),
    risk_finding_repo: RiskFindingRepository = Depends(get_risk_finding_repo),
):
    """Safety 검사 실행"""
    use_case = ScanDraftUseCase(draft_repo, risk_finding_repo)
    findings = await use_case.execute(draft_id)
    return {"findings": findings, "count": len(findings)}


@router.get("/drafts/{draft_id}/findings", response_model=List[RiskFindingResponse])
async def get_findings(
    draft_id: str,
    draft_repo: DraftRepository = Depends(get_draft_repo),
    risk_finding_repo: RiskFindingRepository = Depends(get_risk_finding_repo),
):
    """Safety 검사 결과 조회"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Draft not found")
    
    latest_version = await draft_repo.get_latest_version(draft_id)
    if not latest_version:
        return []
    
    findings = await risk_finding_repo.get_by_draft_version_id(latest_version.id)
    return [
        {
            "id": f.id,
            "category": f.category.value,
            "severity": f.severity.value,
            "snippet": f.snippet,
            "location": f.location_json,
            "status": f.status.value,
        }
        for f in findings
    ]


@router.post("/drafts/{draft_id}/apply")
async def apply_fix(
    draft_id: str,
    request: ApplyFixRequest,
    draft_repo: DraftRepository = Depends(get_draft_repo),
    risk_finding_repo: RiskFindingRepository = Depends(get_risk_finding_repo),
):
    """Safety 검사 결과 적용 (마스킹/삭제/무시)"""
    use_case = ApplyFixUseCase(draft_repo, risk_finding_repo)
    return await use_case.execute(draft_id, request.finding_id, request.action, request.reason)

