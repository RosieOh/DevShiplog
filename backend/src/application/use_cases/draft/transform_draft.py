from typing import Dict, Any
from ports.output.repositories.draft_repository import DraftRepository
from ports.output.repositories.job_repository import JobRepository
from infrastructure.database.models.job import JobType


class TransformDraftUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        job_repo: JobRepository,
    ):
        self.draft_repo = draft_repo
        self.job_repo = job_repo

    async def execute(
        self,
        user_id: str,
        draft_id: str,
        transform_type: str,
    ) -> Dict[str, Any]:
        """Draft 변형 요청"""
        draft = await self.draft_repo.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        # Job 생성
        job = await self.job_repo.create(
            user_id=user_id,
            job_type=JobType.TRANSFORM,
        )

        # Job에 정보 저장
        await self.job_repo.update_status(
            job_id=job.id,
            status=job.status,
            result_ref={"draft_id": draft_id, "transform_type": transform_type},
        )

        return {
            "id": draft_id,
            "job_id": job.id,
            "status": "queued",
        }

