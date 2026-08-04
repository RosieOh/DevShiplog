import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.domain.enums import StyleProfileStatus
from src.infrastructure.database.repositories.style_profile_repository_impl import (
    StyleProfileRepositoryImpl,
)
from src.infrastructure.database.repositories.usage_log_repository_impl import (
    UsageLogRepositoryImpl,
)
from src.infrastructure.database.session import SessionLocal
from src.infrastructure.external.crawler.crawler_service_impl import CrawlerServiceImpl
from src.infrastructure.external.llm.openai_client import OpenAIService
from src.infrastructure.queue.celery_app import celery_app
from src.infrastructure.queue.tasks.support import record_usage
from src.ports.output.services.llm_service import LLMUsage

logger = logging.getLogger(__name__)


async def _collect_and_analyze(
    crawler: CrawlerServiceImpl,
    llm: OpenAIService,
    blog_url: str,
    sample_count: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[LLMUsage], List[str]]:
    posts = await crawler.extract_from_blog(blog_url, sample_count)
    if not posts:
        return None, None, []

    result = await llm.analyze_style(posts)
    return result.value, result.usage, posts


@celery_app.task(name="style_profile.analyze")
def analyze_style_profile_task(profile_id: str, job_id: Optional[str] = None) -> None:
    """Style DNA 분석 Task"""
    db = SessionLocal()
    try:
        style_profile_repo = StyleProfileRepositoryImpl(db)
        usage_repo = UsageLogRepositoryImpl(db)

        profile = style_profile_repo.get_by_id(profile_id)
        if not profile:
            logger.error("StyleProfile %s 을(를) 찾을 수 없습니다", profile_id)
            return

        user_id = profile.user_id
        blog_url = profile.blog_url
        sample_count = profile.sample_count or 5

        style_profile_repo.update_result(profile_id, StyleProfileStatus.RUNNING)

        try:
            analysis, usage, posts = asyncio.run(
                _collect_and_analyze(
                    CrawlerServiceImpl(), OpenAIService(), blog_url, sample_count
                )
            )
            record_usage(usage_repo, user_id, job_id, usage)

            if not posts:
                style_profile_repo.update_result(
                    profile_id,
                    StyleProfileStatus.FAILED,
                    error_text="블로그에서 글을 가져오지 못했습니다. RSS/피드가 공개되어 있는지 확인해주세요.",
                )
                return

            style_profile_repo.update_result(
                profile_id, StyleProfileStatus.SUCCEEDED, profile_json=analysis
            )

        except Exception as exc:
            logger.exception("Style DNA 분석 실패 (profile=%s)", profile_id)
            style_profile_repo.update_result(
                profile_id, StyleProfileStatus.FAILED, error_text=str(exc)
            )
    finally:
        db.close()
