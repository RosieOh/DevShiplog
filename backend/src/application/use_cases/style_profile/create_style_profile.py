from typing import Dict, Any
from ports.output.repositories.style_profile_repository import StyleProfileRepository
from ports.output.services.crawler_service import CrawlerService
from ports.output.services.llm_service import LLMService
from infrastructure.database.models.style_profile import StyleProfileStatus


class CreateStyleProfileUseCase:
    def __init__(
        self,
        style_profile_repo: StyleProfileRepository,
        crawler_service: CrawlerService,
        llm_service: LLMService,
    ):
        self.style_profile_repo = style_profile_repo
        self.crawler_service = crawler_service
        self.llm_service = llm_service

    async def execute(self, user_id: str, blog_url: str, sample_count: int = 5) -> Dict[str, Any]:
        """Style DNA 생성"""
        # Style Profile 생성
        profile = await self.style_profile_repo.create(user_id, blog_url, sample_count)

        # 비동기로 처리하기 위해 Job ID 반환
        # 실제 처리는 Celery Task에서 수행
        return {
            "id": profile.id,
            "status": profile.status.value,
            "blog_url": profile.blog_url,
            "sample_count": profile.sample_count,
        }

