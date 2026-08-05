from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.use_cases.draft.create_draft import CreateDraftUseCase
from src.application.use_cases.draft.transform_draft import TransformDraftUseCase
from src.infrastructure.queue.tasks.draft_generation_tasks import generate_draft_task
from src.infrastructure.queue.tasks.transform_tasks import transform_draft_task
from src.infrastructure.queue import enqueue
from src.ports.input.api.v1.dependencies import (
    get_current_user_id,
    get_draft_repo,
    get_job_repo,
    get_source_repo,
    get_style_profile_repo,
)
from src.ports.input.api.v1.guards import get_owned_draft
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.job_repository import JobRepository
from src.ports.output.repositories.source_repository import SourceRepository
from src.ports.output.repositories.style_profile_repository import StyleProfileRepository

router = APIRouter()


class CreateDraftRequest(BaseModel):
    source_ids: List[str] = Field(min_length=1)
    type: str  # troubleshooting, implementation, retrospective, tutorial, release
    audience: str  # junior, intermediate, interviewer, team
    length: str  # short, default, long
    use_style_profile: bool = True
    style_profile_id: Optional[str] = None


class DraftJobResponse(BaseModel):
    id: str
    job_id: str
    status: str


class TransformDraftRequest(BaseModel):
    transform_type: str  # shorten, expand, simplify, deepen, style_stronger


class UpdateDraftRequest(BaseModel):
    """작성 보조 메타데이터. 본문은 /content 로 따로 저장한다."""

    tags: Optional[List[str]] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=5000)
    checklist: Optional[List[Dict[str, Any]]] = Field(default=None, max_length=100)


class SaveContentRequest(BaseModel):
    """자동저장 — 새 버전을 만들지 않고 최신 버전을 제자리 수정한다."""

    content_md: str
    meta_json: Optional[Dict[str, Any]] = None
    # 클라이언트가 마지막으로 받은 revision. 보내면 낙관적 잠금이 걸린다.
    # 생략하면 기존처럼 무조건 덮어쓴다 (기존 클라이언트 호환).
    base_revision: Optional[int] = None


class CreateVersionRequest(BaseModel):
    """명시적 스냅샷 — 새 버전을 만든다."""

    content_md: str
    meta_json: Optional[Dict[str, Any]] = None
    # 클라이언트가 마지막으로 받은 revision. 보내면 낙관적 잠금이 걸린다.
    # 생략하면 기존처럼 무조건 덮어쓴다 (기존 클라이언트 호환).
    base_revision: Optional[int] = None


def _version_payload(version) -> Optional[Dict[str, Any]]:
    if not version:
        return None
    return {
        "id": version.id,
        "version_no": version.version_no,
        "content_md": version.content_md,
        "meta_json": version.meta_json,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
        "revision": version.revision or 1,
    }


def _draft_payload(draft, latest_version) -> Dict[str, Any]:
    return {
        "id": draft.id,
        "status": draft.status.value,
        "type": draft.type,
        "audience": draft.audience,
        "length_preset": draft.length_preset,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        # 작성 보조 메타데이터. 편집 화면이 매번 따로 조회하지 않도록 같이 내려준다.
        "tags": draft.tags or [],
        "notes": draft.notes,
        "checklist": draft.checklist or [],
        "latest_version": _version_payload(latest_version),
    }


class UpdateOutlineRequest(BaseModel):
    outline: dict  # {title_candidates: [], toc: []}


class CompareVersionsRequest(BaseModel):
    version1_id: str
    version2_id: str


@router.get("")
def list_drafts(
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 목록 조회"""
    drafts = draft_repo.get_by_user_id(user_id)
    return [_draft_payload(d, draft_repo.get_latest_version(d.id)) for d in drafts]


@router.post("", response_model=DraftJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_draft(
    request: CreateDraftRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    source_repo: SourceRepository = Depends(get_source_repo),
    style_profile_repo: StyleProfileRepository = Depends(get_style_profile_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Draft 생성 요청 (실제 생성은 백그라운드에서 수행)"""
    use_case = CreateDraftUseCase(draft_repo, source_repo, style_profile_repo, job_repo)
    result = use_case.execute(
        user_id=user_id,
        source_ids=request.source_ids,
        draft_type=request.type,
        audience=request.audience,
        length_preset=request.length,
        use_style_profile=request.use_style_profile,
        style_profile_id=request.style_profile_id,
    )

    enqueue(generate_draft_task, result["job_id"], result["id"], request.source_ids)
    return result


@router.get("/{draft_id}")
def get_draft(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 조회"""
    draft = get_owned_draft(draft_repo, draft_id, user_id)
    return _draft_payload(draft, draft_repo.get_latest_version(draft_id))


@router.patch("/{draft_id}")
def update_draft(
    draft_id: str,
    request: UpdateDraftRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """태그·메모·체크리스트를 갱신한다. 보낸 항목만 바뀐다."""
    draft = get_owned_draft(draft_repo, draft_id, user_id)

    # exclude_unset 이라야 "빈 값으로 지우기" 와 "안 보냄" 을 구분할 수 있다.
    changes = request.model_dump(exclude_unset=True)
    updated = draft_repo.update_metadata(draft.id, **changes)
    return _draft_payload(updated, draft_repo.get_latest_version(draft_id))


@router.delete("/{draft_id}")
def delete_draft(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """초안을 지운다.

    이미 발행한 글은 남는다. 발행물은 발행 시점의 스냅샷이고, 초안이 사라진다고
    독자가 읽던 글이 없어지면 안 된다 (posts.draft_id 는 SET NULL).
    """
    get_owned_draft(draft_repo, draft_id, user_id)
    draft_repo.delete(draft_id)
    return {"deleted": True}


@router.get("/{draft_id}/versions")
def get_draft_versions(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """Draft 버전 목록 조회"""
    get_owned_draft(draft_repo, draft_id, user_id)
    return [_version_payload(v) for v in draft_repo.get_versions(draft_id)]


@router.put("/{draft_id}/content")
def save_draft_content(
    draft_id: str,
    request: SaveContentRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """자동저장. 최신 버전을 제자리에서 수정한다 (버전이 늘어나지 않는다)."""
    get_owned_draft(draft_repo, draft_id, user_id)

    latest = draft_repo.get_latest_version(draft_id)
    if not latest:
        created = draft_repo.create_version(
            draft_id=draft_id,
            version_no=draft_repo.next_version_no(draft_id),
            content_md=request.content_md,
            meta_json=request.meta_json or {},
        )
        return _version_payload(created)

    updated = draft_repo.update_version_content(
        version_id=latest.id,
        content_md=request.content_md,
        meta_json=request.meta_json,
        expected_revision=request.base_revision,
    )
    return _version_payload(updated)


@router.post("/{draft_id}/versions", status_code=status.HTTP_201_CREATED)
def create_draft_version(
    draft_id: str,
    request: CreateVersionRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
):
    """명시적 버전 저장(스냅샷). 되돌리기 지점을 남기고 싶을 때 호출한다."""
    get_owned_draft(draft_repo, draft_id, user_id)

    latest = draft_repo.get_latest_version(draft_id)
    if latest and (latest.content_md or "") == request.content_md:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="최신 버전과 내용이 같아 새 버전을 만들지 않았습니다.",
        )

    version = draft_repo.create_version(
        draft_id=draft_id,
        version_no=draft_repo.next_version_no(draft_id),
        content_md=request.content_md,
        meta_json=request.meta_json or (latest.meta_json if latest else {}),
    )
    return _version_payload(version)


@router.post(
    "/{draft_id}/transform",
    response_model=DraftJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def transform_draft(
    draft_id: str,
    request: TransformDraftRequest,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Draft 변형 (짧게/길게/쉽게/깊게)"""
    use_case = TransformDraftUseCase(draft_repo, job_repo)
    result = use_case.execute(user_id, draft_id, request.transform_type)

    enqueue(transform_draft_task, result["job_id"], draft_id, request.transform_type)
    return result
