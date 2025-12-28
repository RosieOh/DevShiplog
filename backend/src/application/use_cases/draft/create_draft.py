from typing import Dict, Any
from ports.output.repositories.draft_repository import DraftRepository
from ports.output.repositories.source_repository import SourceRepository
from ports.output.repositories.style_profile_repository import StyleProfileRepository
from ports.output.repositories.job_repository import JobRepository
from infrastructure.database.models.job import JobType


class CreateDraftUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        source_repo: SourceRepository,
        style_profile_repo: StyleProfileRepository,
        job_repo: JobRepository,
    ):
        self.draft_repo = draft_repo
        self.source_repo = source_repo
        self.style_profile_repo = style_profile_repo
        self.job_repo = job_repo

    async def execute(
        self,
        user_id: str,
        source_ids: list[str],
        draft_type: str,
        audience: str,
        length_preset: str,
        use_style_profile: bool,
        style_profile_id: str = None,
    ) -> Dict[str, Any]:
        """Draft 생성 요청"""
        # Style Profile 확인
        final_style_profile_id = None
        if use_style_profile and style_profile_id:
            profile = await self.style_profile_repo.get_by_id(style_profile_id)
            if profile:
                final_style_profile_id = profile.id

        # Draft 생성
        draft = await self.draft_repo.create(
            user_id=user_id,
            draft_type=draft_type,
            audience=audience,
            length_preset=length_preset,
            style_profile_id=final_style_profile_id,
        )

        # Job 생성 (비동기 처리)
        job = await self.job_repo.create(
            user_id=user_id,
            job_type=JobType.DRAFT,
        )

        # Job에 draft_id 저장
        await self.job_repo.update_status(
            job_id=job.id,
            status=job.status,
            result_ref={"draft_id": draft.id, "source_ids": source_ids},
        )

        return {
            "id": draft.id,
            "job_id": job.id,
            "status": "queued",
        }

