import asyncio
import logging
from typing import Tuple

from src.domain.enums import JobStatus
from src.infrastructure.database.repositories.draft_repository_impl import DraftRepositoryImpl
from src.infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl
from src.infrastructure.database.repositories.usage_log_repository_impl import (
    UsageLogRepositoryImpl,
)
from src.infrastructure.database.session import SessionLocal
from src.infrastructure.external.llm.openai_client import OpenAIService
from src.infrastructure.queue.celery_app import celery_app
from src.infrastructure.queue.tasks.support import ProgressWriter, record_usage
from src.ports.output.services.llm_service import LLMUsage

logger = logging.getLogger(__name__)


async def _run_transform(
    llm: OpenAIService,
    content: str,
    transform_type: str,
    progress: ProgressWriter,
) -> Tuple[str, LLMUsage]:
    stream = llm.transform_draft(draft_content=content, transform_type=transform_type)
    transformed = await stream.collect(on_chunk=progress.on_chunk)
    return transformed, stream.usage


@celery_app.task(name="draft.transform")
def transform_draft_task(job_id: str, draft_id: str, transform_type: str) -> None:
    """Draft 변형 Task"""
    db = SessionLocal()
    try:
        draft_repo = DraftRepositoryImpl(db)
        job_repo = JobRepositoryImpl(db)
        usage_repo = UsageLogRepositoryImpl(db)

        job = job_repo.get_by_id(job_id)
        if not job:
            logger.error("Job %s 을(를) 찾을 수 없습니다", job_id)
            return

        try:
            job_repo.update_status(job_id, JobStatus.RUNNING, progress=10)

            draft = draft_repo.get_by_id(draft_id)
            if not draft:
                raise ValueError("Draft 를 찾을 수 없습니다.")

            latest_version = draft_repo.get_latest_version(draft_id)
            if not latest_version:
                raise ValueError("변형할 버전이 없습니다.")

            progress = ProgressWriter(job_repo, job_id, start_progress=20, end_progress=85)
            transformed, usage = asyncio.run(
                _run_transform(
                    OpenAIService(),
                    latest_version.content_md or "",
                    transform_type,
                    progress,
                )
            )
            record_usage(usage_repo, job.user_id, job_id, usage)

            if not transformed.strip():
                raise ValueError("LLM 이 빈 응답을 반환했습니다.")

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=90)

            version_no = draft_repo.next_version_no(draft_id)
            draft_repo.create_version(
                draft_id=draft_id,
                version_no=version_no,
                content_md=transformed,
                meta_json=latest_version.meta_json,
            )

            job_repo.update_status(
                job_id,
                JobStatus.SUCCEEDED,
                progress=100,
                result_ref={
                    "draft_id": draft_id,
                    "version_no": version_no,
                    "content": transformed,
                },
            )

        except Exception as exc:
            logger.exception("Draft 변형 실패 (job=%s)", job_id)
            job_repo.update_status(job_id, JobStatus.FAILED, error_text=str(exc))
    finally:
        db.close()
