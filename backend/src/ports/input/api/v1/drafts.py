from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from ports.input.api.v1.dependencies import (
    get_draft_repo, get_source_repo, get_style_profile_repo, get_job_repo, get_db
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


class UpdateDraftRequest(BaseModel):
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    checklist: Optional[List[dict]] = None


class GenerateOutlineRequest(BaseModel):
    source_ids: List[str]
    type: str
    audience: str
    length: str


class UpdateOutlineRequest(BaseModel):
    outline: dict  # {title_candidates: [], toc: []}


class CompareVersionsRequest(BaseModel):
    version1_id: str
    version2_id: str


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


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    db: Session = Depends(get_db),
):
    """Draft 삭제"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Soft delete (status를 archived로 변경)
    from infrastructure.database.models.draft import DraftStatus
    draft.status = DraftStatus.ARCHIVED
    db.commit()
    
    return {"message": "Draft deleted successfully"}


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


@router.post("/generate-outline")
async def generate_outline(
    request: GenerateOutlineRequest,
    user_id: str = Depends(get_current_user_id),
    source_repo: SourceRepository = Depends(get_source_repo),
    llm_service = Depends(lambda: __import__('infrastructure.external.llm.openai_client', fromlist=['OpenAIService']).OpenAIService()),
):
    """목차 생성 (초안 생성 전)"""
    sources = await source_repo.get_by_ids(request.source_ids)
    if not sources:
        raise HTTPException(status_code=404, detail="Sources not found")
    
    source_content = "\n\n".join([s.content or "" for s in sources])
    
    outline = await llm_service.generate_outline(
        source_content=source_content,
        draft_type=request.type,
        audience=request.audience,
        length_preset=request.length,
    )
    
    return {"outline": outline}


@router.get("/{draft_id}/outline")
async def get_draft_outline(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 목차 조회"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {"outline": draft.outline or {}}


@router.put("/{draft_id}/outline")
async def update_draft_outline(
    draft_id: str,
    request: UpdateOutlineRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    db: Session = Depends(get_db),
):
    """Draft 목차 업데이트"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    draft.outline = request.outline
    db.commit()
    
    return {"message": "Outline updated successfully"}


@router.put("/{draft_id}")
async def update_draft(
    draft_id: str,
    request: UpdateDraftRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    db: Session = Depends(get_db),
):
    """Draft 메타데이터 업데이트 (태그, 노트, 체크리스트)"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if request.tags is not None:
        draft.tags = request.tags
    if request.notes is not None:
        draft.notes = request.notes
    if request.checklist is not None:
        draft.checklist = request.checklist
    
    db.commit()
    
    return {"message": "Draft updated successfully"}


@router.get("/{draft_id}/compare")
async def compare_versions(
    draft_id: str,
    version1_id: str,
    version2_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """버전 비교"""
    draft = await draft_repo.get_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    versions = await draft_repo.get_versions(draft_id)
    v1 = next((v for v in versions if v.id == version1_id), None)
    v2 = next((v for v in versions if v.id == version2_id), None)
    
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # 간단한 diff 계산 (실제로는 diff 라이브러리 사용 권장)
    content1 = v1.content_md or ""
    content2 = v2.content_md or ""
    
    # 통계
    words1 = len(content1.split())
    words2 = len(content2.split())
    lines1 = len(content1.split('\n'))
    lines2 = len(content2.split('\n'))
    
    return {
        "version1": {
            "id": v1.id,
            "version_no": v1.version_no,
            "content": content1,
            "word_count": words1,
            "line_count": lines1,
        },
        "version2": {
            "id": v2.id,
            "version_no": v2.version_no,
            "content": content2,
            "word_count": words2,
            "line_count": lines2,
        },
        "diff": {
            "word_diff": words2 - words1,
            "line_diff": lines2 - lines1,
        }
    }

