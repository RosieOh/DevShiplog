from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ports.input.api.v1.dependencies import get_style_profile_repo, get_crawler_service, get_llm_service
from ports.input.api.v1.auth import get_current_user_id
from ports.output.repositories.style_profile_repository import StyleProfileRepository
from ports.output.services.crawler_service import CrawlerService
from ports.output.services.llm_service import LLMService
from application.use_cases.style_profile.create_style_profile import CreateStyleProfileUseCase
from infrastructure.queue.tasks.style_profile_tasks import analyze_style_profile_task

router = APIRouter()


class CreateStyleProfileRequest(BaseModel):
    blog_url: str
    sample_count: int = 5


class StyleProfileResponse(BaseModel):
    id: str
    status: str
    blog_url: str
    sample_count: int


@router.post("", response_model=StyleProfileResponse)
async def create_style_profile(
    request: CreateStyleProfileRequest,
    user_id: str = Depends(get_current_user_id),
    style_profile_repo: StyleProfileRepository = Depends(get_style_profile_repo),
    crawler_service: CrawlerService = Depends(get_crawler_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Style DNA 생성 요청"""
    use_case = CreateStyleProfileUseCase(style_profile_repo, crawler_service, llm_service)
    result = await use_case.execute(user_id, request.blog_url, request.sample_count)
    
    # 비동기 Task 실행
    analyze_style_profile_task.delay(result["id"])
    
    return result


@router.get("/{profile_id}", response_model=StyleProfileResponse)
async def get_style_profile(
    profile_id: str,
    user_id: str = Depends(get_current_user_id),
    style_profile_repo: StyleProfileRepository = Depends(get_style_profile_repo),
):
    """Style DNA 조회"""
    profile = await style_profile_repo.get_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    if profile.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {
        "id": profile.id,
        "status": profile.status.value,
        "blog_url": profile.blog_url,
        "sample_count": profile.sample_count,
    }

