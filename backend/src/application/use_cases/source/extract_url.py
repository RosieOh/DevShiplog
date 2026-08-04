import logging
from typing import Any, Dict, List

from src.application.errors import ValidationError
from src.domain.enums import SourceType
from src.ports.output.repositories.source_repository import SourceRepository
from src.ports.output.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)

MAX_URLS_PER_REQUEST = 10


class ExtractURLUseCase:
    def __init__(self, source_repo: SourceRepository, crawler_service: CrawlerService):
        self.source_repo = source_repo
        self.crawler_service = crawler_service

    async def execute(self, user_id: str, urls: List[str]) -> List[Dict[str, Any]]:
        """URL 목록에서 본문을 추출해 Source 로 저장한다.

        일부 URL 이 실패해도 나머지는 계속 처리하되, 실패한 항목은
        status="failed" 와 오류 메시지로 표시하고 본문에는 저장하지 않는다.
        """
        cleaned = [u.strip() for u in urls if u and u.strip()]
        if not cleaned:
            raise ValidationError("최소 하나의 URL 이 필요합니다.")
        if len(cleaned) > MAX_URLS_PER_REQUEST:
            raise ValidationError(f"한 번에 최대 {MAX_URLS_PER_REQUEST}개까지 처리할 수 있습니다.")

        results = []
        for url in cleaned:
            try:
                extracted = await self.crawler_service.extract_from_url(url)
            except Exception as exc:  # 크롤링 실패는 개별 항목 실패로 처리
                logger.info("소스 추출 실패 (%s): %s", url, exc)
                results.append(
                    {
                        "id": None,
                        "type": SourceType.URL.value,
                        "title": url,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                continue

            source = self.source_repo.create(
                user_id=user_id,
                source_type=SourceType.URL,
                origin=url,
                title=extracted.get("title") or url,
                content=extracted.get("content", ""),
                extracted_json={
                    "headings": extracted.get("headings", []),
                    "codeBlocks": extracted.get("codeBlocks", []),
                    "images": extracted.get("images", []),
                },
            )
            results.append(
                {
                    "id": source.id,
                    "type": source.type.value,
                    "title": source.title,
                    "status": "succeeded",
                    "error": None,
                }
            )

        return results
