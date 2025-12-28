from infrastructure.queue.celery_app import celery_app
from infrastructure.database.session import SessionLocal
from infrastructure.database.models.job import JobStatus
from infrastructure.database.repositories.draft_repository_impl import DraftRepositoryImpl
from infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl
from infrastructure.external.llm.openai_client import OpenAIService


@celery_app.task
def transform_draft_task(job_id: str, draft_id: str, transform_type: str):
    """Draft 변형 Task"""
    db = SessionLocal()
    try:
        draft_repo = DraftRepositoryImpl(db)
        job_repo = JobRepositoryImpl(db)
        llm_service = OpenAIService()

        # Job 상태 업데이트
        job = job_repo.get_by_id(job_id)
        if not job:
            return

        job_repo.update_status(job_id, JobStatus.RUNNING, progress=10)

        try:
            # Draft 및 최신 버전 조회
            draft = draft_repo.get_by_id(draft_id)
            if not draft:
                raise ValueError(f"Draft {draft_id} not found")

            latest_version = draft_repo.get_latest_version(draft_id)
            if not latest_version:
                raise ValueError(f"No version found for draft {draft_id}")

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=30)

            import asyncio
            # 변형 적용 (스트리밍)
            async def collect_transformed():
                content_parts = []
                async for chunk in llm_service.transform_draft(
                    draft_content=latest_version.content_md or "",
                    transform_type=transform_type,
                ):
                    content_parts.append(chunk)
                return "".join(content_parts)

            transformed_content = asyncio.run(collect_transformed())

            job_repo.update_status(job_id, JobStatus.RUNNING, progress=80)

            # 새 버전 생성
            new_version_no = latest_version.version_no + 1
            draft_repo.create_version(
                draft_id=draft_id,
                version_no=new_version_no,
                content_md=transformed_content,
                meta_json=latest_version.meta_json,
            )

            job_repo.update_status(
                job_id,
                JobStatus.SUCCEEDED,
                progress=100,
                result_ref={"draft_id": draft_id, "version_no": new_version_no},
            )

        except Exception as e:
            job_repo.update_status(
                job_id,
                JobStatus.FAILED,
                error_text=str(e),
            )

    finally:
        db.close()

