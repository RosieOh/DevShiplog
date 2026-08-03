from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.use_cases.style_profile.create_style_profile import CreateStyleProfileUseCase
from src.infrastructure.queue.tasks.style_profile_tasks import analyze_style_profile_task
from src.ports.input.api.v1.dependencies import (
    get_current_user_id,
    get_job_repo,
    get_style_profile_repo,
)
from src.ports.output.repositories.job_repository import JobRepository
from src.ports.output.repositories.style_profile_repository import StyleProfileRepository

router = APIRouter()


class CreateStyleProfileRequest(BaseModel):
    blog_url: str = Field(max_length=500)
    sample_count: int = Field(default=5, ge=1, le=10)


class StyleProfileResponse(BaseModel):
    id: str
    status: str
    blog_url: str
    sample_count: int
    profile_json: Optional[Dict[str, Any]] = None
    error_text: Optional[str] = None


def _payload(profile) -> Dict[str, Any]:
    return {
        "id": profile.id,
        "status": profile.status.value,
        "blog_url": profile.blog_url,
        "sample_count": profile.sample_count,
        "profile_json": profile.profile_json,
        "error_text": profile.error_text,
    }


@router.post("", response_model=StyleProfileResponse, status_code=status.HTTP_202_ACCEPTED)
def create_style_profile(
    request: CreateStyleProfileRequest,
    user_id: str = Depends(get_current_user_id),
    style_profile_repo: StyleProfileRepository = Depends(get_style_profile_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Style DNA 생성 요청 (실제 분석은 백그라운드에서 수행)"""
    use_case = CreateStyleProfileUseCase(style_profile_repo, job_repo)
    result = use_case.execute(user_id, request.blog_url, request.sample_count)

    analyze_style_profile_task.delay(result["id"])
    return result


@router.get("", response_model=List[StyleProfileResponse])
def list_style_profiles(
    user_id: str = Depends(get_current_user_id),
    style_profile_repo: StyleProfileRepository = Depends(get_style_profile_repo),
):
    """내 Style DNA 목록"""
    return [_payload(p) for p in style_profile_repo.get_by_user_id(user_id)]


@router.get("/{profile_id}", response_model=StyleProfileResponse)
def get_style_profile(
    profile_id: str,
    user_id: str = Depends(get_current_user_id),
    style_profile_repo: StyleProfileRepository = Depends(get_style_profile_repo),
):
    """Style DNA 조회"""
    profile = style_profile_repo.get_by_id(profile_id)
    if not profile or profile.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="스타일 프로필을 찾을 수 없습니다."
        )
    return _payload(profile)
