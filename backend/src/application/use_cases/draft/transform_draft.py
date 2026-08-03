from typing import Any, Dict

from src.application.errors import NotFoundError, PermissionDeniedError, ValidationError
from src.application.services.quota import assert_within_quota
from src.domain.enums import JobType, TransformType
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.job_repository import JobRepository


class TransformDraftUseCase:
    def __init__(self, draft_repo: DraftRepository, job_repo: JobRepository):
        self.draft_repo = draft_repo
        self.job_repo = job_repo

    def execute(self, user_id: str, draft_id: str, transform_type: str) -> Dict[str, Any]:
        """Draft 변형 요청. 실제 변형은 Celery Task 가 수행한다."""
        try:
            TransformType(transform_type)
        except ValueError:
            raise ValidationError(f"지원하지 않는 변형 유형입니다: {transform_type}") from None

        draft = self.draft_repo.get_by_id(draft_id)
        if not draft:
            raise NotFoundError("Draft 를 찾을 수 없습니다.")
        if draft.user_id != user_id:
            raise PermissionDeniedError("이 Draft 에 접근할 수 없습니다.")

        if not self.draft_repo.get_latest_version(draft_id):
            raise ValidationError("아직 생성이 끝나지 않은 Draft 는 변형할 수 없습니다.")

        assert_within_quota(self.job_repo, user_id)

        job = self.job_repo.create(
            user_id=user_id,
            job_type=JobType.TRANSFORM,
            result_ref={"draft_id": draft_id, "transform_type": transform_type},
        )

        return {"id": draft_id, "job_id": job.id, "status": job.status.value}
