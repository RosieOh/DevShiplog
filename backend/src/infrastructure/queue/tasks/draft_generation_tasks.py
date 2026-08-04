import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.domain.enums import JobStatus
from src.infrastructure.database.repositories.draft_repository_impl import DraftRepositoryImpl
from src.infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl
from src.infrastructure.database.repositories.source_repository_impl import SourceRepositoryImpl
from src.infrastructure.database.repositories.style_profile_repository_impl import (
    StyleProfileRepositoryImpl,
)
from src.infrastructure.database.repositories.usage_log_repository_impl import (
    UsageLogRepositoryImpl,
)
from src.infrastructure.database.session import SessionLocal
from src.infrastructure.external.llm.openai_client import OpenAIService
from src.infrastructure.queue.celery_app import celery_app
from src.infrastructure.queue.tasks.support import ProgressWriter, record_usage
from src.ports.output.services.llm_service import LLMUsage

logger = logging.getLogger(__name__)


async def _run_generation(
    llm: OpenAIService,
    *,
    source_content: str,
    draft_type: str,
    audience: str,
    length_preset: str,
    style_profile: Optional[Dict[str, Any]],
    progress: ProgressWriter,
) -> Tuple[str, Dict[str, Any], List[LLMUsage]]:
    """outline → 본문 스트리밍 → (선택) 스타일 적용을 한 이벤트 루프에서 수행한다."""
    usages: List[LLMUsage] = []

    outline_result = await llm.generate_outline(
        source_content=source_content,
        draft_type=draft_type,
        audience=audience,
        length_preset=length_preset,
    )
    usages.append(outline_result.usage)
    outline = outline_result.value

    stream = llm.generate_draft(
        outline=outline,
        source_content=source_content,
        draft_type=draft_type,
        audience=audience,
        length_preset=length_preset,
    )
    content = await stream.collect(on_chunk=progress.on_chunk)
    if stream.usage:
        usages.append(stream.usage)

    if style_profile:
        styled = await llm.apply_style(content, style_profile)
        usages.append(styled.usage)
        content = styled.value

    return content, outline, usages


@celery_app.task(name="draft.generate")
def generate_draft_task(job_id: str, draft_id: str, source_ids: List[str]) -> None:
    """Draft 생성 Task"""
    db = SessionLocal()
    try:
        draft_repo = DraftRepositoryImpl(db)
        source_repo = SourceRepositoryImpl(db)
        style_profile_repo = StyleProfileRepositoryImpl(db)
        job_repo = JobRepositoryImpl(db)
        usage_repo = UsageLogRepositoryImpl(db)

        job = job_repo.get_by_id(job_id)
        if not job:
            logger.error("Job %s 을(를) 찾을 수 없습니다", job_id)
            return

        try:
            job_repo.update_status(job_id, JobStatus.RUNNING, progress=5)

            draft = draft_repo.get_by_id(draft_id)
            if not draft:
                raise ValueError("Draft 를 찾을 수 없습니다.")

            sources = source_repo.get_by_ids(source_ids)
            if not sources:
                raise ValueError("소스를 찾을 수 없습니다.")

            source_content = "\n\n".join(s.content or "" for s in sources).strip()
            if not source_content:
                raise ValueError("소스 본문이 비어 있습니다.")

            style_profile = None
            if draft.style_profile_id:
                profile = style_profile_repo.get_by_id(draft.style_profile_id)
                if profile and profile.profile_json and "error" not in profile.profile_json:
                    style_profile = profile.profile_json

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=15)

            progress = ProgressWriter(job_repo, job_id, start_progress=20, end_progress=85)
            content, outline, usages = asyncio.run(
                _run_generation(
                    OpenAIService(),
                    source_content=source_content,
                    draft_type=draft.type or "implementation",
                    audience=draft.audience or "intermediate",
                    length_preset=draft.length_preset or "default",
                    style_profile=style_profile,
                    progress=progress,
                )
            )

            for usage in usages:
                record_usage(usage_repo, job.user_id, job_id, usage)

            if not content.strip():
                raise ValueError("LLM 이 빈 응답을 반환했습니다.")

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=90)

            titles = outline.get("titleCandidates") or []
            version_no = draft_repo.next_version_no(draft_id)
            draft_repo.create_version(
                draft_id=draft_id,
                version_no=version_no,
                content_md=content,
                meta_json={
                    "title": titles[0] if titles else "",
                    "titleCandidates": titles,
                    "toc": outline.get("toc", []),
                    "keyPoints": outline.get("keyPoints", []),
                },
            )

            job_repo.update_status(
                job_id,
                JobStatus.SUCCEEDED,
                progress=100,
                result_ref={"draft_id": draft_id, "version_no": version_no, "content": content},
            )

        except Exception as exc:
            logger.exception("Draft 생성 실패 (job=%s)", job_id)
            job_repo.update_status(job_id, JobStatus.FAILED, error_text=str(exc))
    finally:
        db.close()
