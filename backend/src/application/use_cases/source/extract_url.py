from typing import List, Dict, Any
from ports.output.repositories.source_repository import SourceRepository
from ports.output.services.crawler_service import CrawlerService
from infrastructure.database.models.source import SourceType


class ExtractURLUseCase:
    def __init__(
        self,
        source_repo: SourceRepository,
        crawler_service: CrawlerService,
    ):
        self.source_repo = source_repo
        self.crawler_service = crawler_service

    async def execute(self, user_id: str, urls: List[str]) -> List[Dict[str, Any]]:
        """URL에서 소스 추출"""
        sources = []
        for url in urls:
            try:
                extracted = await self.crawler_service.extract_from_url(url)
                source = await self.source_repo.create(
                    user_id=user_id,
                    source_type=SourceType.URL,
                    origin=url,
                    title=extracted.get("title", url),
                    content=extracted.get("content", ""),
                    extracted_json={
                        "headings": extracted.get("headings", []),
                        "codeBlocks": extracted.get("codeBlocks", []),
                        "images": extracted.get("images", []),
                    },
                )
                sources.append({
                    "id": source.id,
                    "type": source.type.value,
                    "title": source.title,
                    "status": "succeeded",
                })
            except Exception as e:
                # 실패해도 소스는 생성 (에러 정보 포함)
                source = await self.source_repo.create(
                    user_id=user_id,
                    source_type=SourceType.URL,
                    origin=url,
                    title=url,
                    content=f"추출 실패: {str(e)}",
                )
                sources.append({
                    "id": source.id,
                    "type": source.type.value,
                    "title": source.title,
                    "status": "failed",
                })

        return sources

