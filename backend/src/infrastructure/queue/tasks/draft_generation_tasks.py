from infrastructure.queue.celery_app import celery_app
from infrastructure.database.session import SessionLocal
from infrastructure.database.models.job import JobStatus
from infrastructure.database.repositories.draft_repository_impl import DraftRepositoryImpl
from infrastructure.database.repositories.source_repository_impl import SourceRepositoryImpl
from infrastructure.database.repositories.style_profile_repository_impl import StyleProfileRepositoryImpl
from infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl
from infrastructure.external.llm.openai_client import OpenAIService


@celery_app.task
def generate_draft_task(job_id: str, draft_id: str, source_ids: list[str]):
    """Draft 생성 Task"""
    db = SessionLocal()
    try:
        draft_repo = DraftRepositoryImpl(db)
        source_repo = SourceRepositoryImpl(db)
        style_profile_repo = StyleProfileRepositoryImpl(db)
        job_repo = JobRepositoryImpl(db)
        llm_service = OpenAIService()

        # Job 상태 업데이트
        job = job_repo.get_by_id(job_id)
        if not job:
            return

        job_repo.update_status(job_id, JobStatus.RUNNING, progress=10)

        try:
            # Draft 조회
            draft = draft_repo.get_by_id(draft_id)
            if not draft:
                raise ValueError(f"Draft {draft_id} not found")

            # Sources 조회
            sources = source_repo.get_by_ids(source_ids)
            if not sources:
                raise ValueError("No sources found")

            # 소스 내용 합치기
            source_content = "\n\n".join([s.content or "" for s in sources])

            # Style Profile 조회
            style_profile = None
            if draft.style_profile_id:
                profile = style_profile_repo.get_by_id(draft.style_profile_id)
                if profile and profile.profile_json:
                    style_profile = profile.profile_json

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=30)

            import asyncio
            # Outline 생성
            outline = asyncio.run(llm_service.generate_outline(
                source_content=source_content,
                draft_type=draft.type or "implementation",
                audience=draft.audience or "intermediate",
                length_preset=draft.length_preset or "default",
            ))

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=50)

            # Draft 생성 (스트리밍)
            async def collect_draft():
                content_parts = []
                async for chunk in llm_service.generate_draft(
                    outline=outline,
                    source_content=source_content,
                    draft_type=draft.type or "implementation",
                    audience=draft.audience or "intermediate",
                    length_preset=draft.length_preset or "default",
                ):
                    content_parts.append(chunk)
                return "".join(content_parts)

            draft_content = asyncio.run(collect_draft())

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=80)

            # Style 적용 (있는 경우)
            if style_profile:
                draft_content = asyncio.run(llm_service.apply_style(draft_content, style_profile))

            # Version 생성
            draft_repo.create_version(
                draft_id=draft_id,
                version_no=1,
                content_md=draft_content,
                meta_json={
                    "title": outline.get("titleCandidates", [""])[0] if outline.get("titleCandidates") else "",
                    "toc": outline.get("toc", []),
                    "keyPoints": outline.get("keyPoints", []),
                },
            )

            job_repo.update_status(
                job_id,
                JobStatus.SUCCEEDED,
                progress=100,
                result_ref={"draft_id": draft_id},
            )

        except Exception as e:
            job_repo.update_status(
                job_id,
                JobStatus.FAILED,
                error_text=str(e),
            )

    finally:
        db.close()

