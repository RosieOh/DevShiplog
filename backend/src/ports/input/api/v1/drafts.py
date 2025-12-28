from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ports.input.api.v1.dependencies import (
    get_draft_repo, get_source_repo, get_style_profile_repo, get_job_repo
)
from ports.input.api.v1.auth import get_current_user_id
from ports.output.repositories.draft_repository import DraftRepository
from ports.output.repositories.source_repository import SourceRepository
from ports.output.repositories.style_profile_repository import StyleProfileRepository
from ports.output.repositories.job_repository import JobRepository
from application.use_cases.draft.create_draft import CreateDraftUseCase
from application.use_cases.draft.transform_draft import TransformDraftUseCase
from infrastructure.queue.tasks.draft_generation_tasks import generate_draft_task
from infrastructure.queue.tasks.transform_tasks import transform_draft_task

router = APIRouter()


class CreateDraftRequest(BaseModel):
    source_ids: List[str]
    type: str  # troubleshooting, implementation, retrospective, tutorial, release
    audience: str  # junior, intermediate, interviewer, team
    length: str  # short, default, long
    use_style_profile: bool = True
    style_profile_id: Optional[str] = None


class DraftResponse(BaseModel):
    id: str
    job_id: str
    status: str


class TransformDraftRequest(BaseModel):
    transform_type: str  # shorten, expand, simplify, deepen, style_stronger


class UpdateVersionRequest(BaseModel):
    content_md: str
    meta_json: Optional[dict] = None


@router.get("")
async def list_drafts(
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 목록 조회"""
    drafts = await draft_repo.get_by_user_id(user_id)
    result = []
    for draft in drafts:
        latest_version = await draft_repo.get_latest_version(draft.id)
        result.append({
            "id": draft.id,
            "status": draft.status.value,
            "type": draft.type,
            "audience": draft.audience,
            "length_preset": draft.length_preset,
            "latest_version": {
                "version_no": latest_version.version_no if latest_version else None,
                "content_md": latest_version.content_md if latest_version else None,
                "meta_json": latest_version.meta_json if latest_version else None,
            } if latest_version else None,
        })
    return result


@router.post("", response_model=DraftResponse)
async def create_draft(
    request: CreateDraftRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    source_repo: SourceRepository = Depends(get_source_repo),
    style_profile_repo: StyleProfileRepository = Depends(get_style_profile_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Draft 생성 요청"""
    use_case = CreateDraftUseCase(draft_repo, source_repo, style_profile_repo, job_repo)
    result = await use_case.execute(
        user_id=user_id,
        source_ids=request.source_ids,
        draft_type=request.type,
        audience=request.audience,
        length_preset=request.length,
        use_style_profile=request.use_style_profile,
        style_profile_id=request.style_profile_id,
    )
    
    # 비동기 Task 실행
    generate_draft_task.delay(result["job_id"], result["id"], request.source_ids)
    
    return result


@router.get("/{draft_id}")
async def get_draft(
    draft_id: str,
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 조회"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    latest_version = await draft_repo.get_latest_version(draft_id)
    
    return {
        "id": draft.id,
        "status": draft.status.value,
        "type": draft.type,
        "audience": draft.audience,
        "length_preset": draft.length_preset,
        "latest_version": {
            "version_no": latest_version.version_no if latest_version else None,
            "content_md": latest_version.content_md if latest_version else None,
            "meta_json": latest_version.meta_json if latest_version else None,
        } if latest_version else None,
    }


@router.get("/{draft_id}/versions")
async def get_draft_versions(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 버전 목록 조회"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    versions = await draft_repo.get_versions(draft_id)
    return [
        {
            "id": v.id,
            "version_no": v.version_no,
            "content_md": v.content_md,
            "meta_json": v.meta_json,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.put("/{draft_id}/version")
async def update_draft_version(
    draft_id: str,
    request: UpdateVersionRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 버전 업데이트"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 새 버전 생성
    latest_version = await draft_repo.get_latest_version(draft_id)
    new_version_no = (latest_version.version_no + 1) if latest_version else 1
    
    await draft_repo.create_version(
        draft_id=draft_id,
        version_no=new_version_no,
        content_md=request.content_md,
        meta_json=request.meta_json or {},
    )
    
    return {"message": "Version updated successfully"}


@router.post("/{draft_id}/transform", response_model=DraftResponse)
async def transform_draft(
    draft_id: str,
    request: TransformDraftRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Draft 변형 (짧게/길게/쉽게/깊게)"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    use_case = TransformDraftUseCase(draft_repo, job_repo)
    result = await use_case.execute(user_id, draft_id, request.transform_type)
    
    # 비동기 Task 실행
    transform_draft_task.delay(result["job_id"], draft_id, request.transform_type)
    
    return result

