from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.application.errors import ValidationError
from src.application.use_cases.source.extract_text import ExtractTextUseCase
from src.application.use_cases.source.extract_url import ExtractURLUseCase
from src.ports.input.api.v1.dependencies import (
    get_crawler_service,
    get_current_user_id,
    get_source_repo,
)
from src.ports.output.repositories.source_repository import SourceRepository
from src.ports.output.services.crawler_service import CrawlerService

router = APIRouter()


class ExtractRequest(BaseModel):
    """urls 또는 raw_text 중 하나를 보낸다.

    예전에는 Union[…] 두 모델을 받았는데, 어느 쪽으로 파싱될지 모호해서
    하나의 모델로 합치고 검증을 명시적으로 한다.
    """

    urls: Optional[List[str]] = None
    raw_text: Optional[str] = None


class SourceResponse(BaseModel):
    id: Optional[str] = None
    type: str
    title: str
    status: str
    error: Optional[str] = None


@router.post("/extract", response_model=List[SourceResponse])
async def extract_sources(
    request: ExtractRequest,
    user_id: str = Depends(get_current_user_id),
    source_repo: SourceRepository = Depends(get_source_repo),
    crawler_service: CrawlerService = Depends(get_crawler_service),
):
    """URL 또는 텍스트에서 소스 추출"""
    has_urls = bool(request.urls and any(u.strip() for u in request.urls))
    has_text = bool(request.raw_text and request.raw_text.strip())

    if has_urls == has_text:
        raise ValidationError("urls 또는 raw_text 중 정확히 하나를 보내야 합니다.")

    if has_urls:
        use_case = ExtractURLUseCase(source_repo, crawler_service)
        return await use_case.execute(user_id, request.urls or [])

    text_use_case = ExtractTextUseCase(source_repo)
    return [text_use_case.execute(user_id, request.raw_text or "")]
