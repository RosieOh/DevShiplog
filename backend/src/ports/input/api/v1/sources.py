from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Union
from ports.input.api.v1.dependencies import get_source_repo, get_crawler_service
from ports.input.api.v1.auth import get_current_user_id
from ports.output.repositories.source_repository import SourceRepository
from ports.output.services.crawler_service import CrawlerService
from application.use_cases.source.extract_url import ExtractURLUseCase
from application.use_cases.source.extract_text import ExtractTextUseCase

router = APIRouter()


class ExtractURLsRequest(BaseModel):
    urls: List[str]


class ExtractTextRequest(BaseModel):
    raw_text: str


class SourceResponse(BaseModel):
    id: str
    type: str
    title: str
    status: str


@router.post("/extract", response_model=List[SourceResponse])
async def extract_sources(
    request: Union[ExtractURLsRequest, ExtractTextRequest],
    user_id: str = Depends(get_current_user_id),
    source_repo: SourceRepository = Depends(get_source_repo),
    crawler_service: CrawlerService = Depends(get_crawler_service),
):
    """URL 또는 텍스트에서 소스 추출"""
    if isinstance(request, ExtractURLsRequest):
        use_case = ExtractURLUseCase(source_repo, crawler_service)
        return await use_case.execute(user_id, request.urls)
    else:
        use_case = ExtractTextUseCase(source_repo)
        result = await use_case.execute(user_id, request.raw_text)
        return [result]

