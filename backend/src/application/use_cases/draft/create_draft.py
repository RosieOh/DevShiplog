from typing import Any, Dict, List, Optional

from src.application.errors import NotFoundError, ValidationError
from src.application.services.quota import assert_within_quota
from src.domain.enums import JobType
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.job_repository import JobRepository
from src.ports.output.repositories.source_repository import SourceRepository
from src.ports.output.repositories.style_profile_repository import StyleProfileRepository

ALLOWED_TYPES = {"troubleshooting", "implementation", "retrospective", "tutorial", "release"}
ALLOWED_AUDIENCES = {"junior", "intermediate", "interviewer", "team"}
ALLOWED_LENGTHS = {"short", "default", "long"}


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

    def execute(
        self,
        user_id: str,
        source_ids: List[str],
        draft_type: str,
        audience: str,
        length_preset: str,
        use_style_profile: bool,
        style_profile_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Draft 생성 요청. 실제 생성은 Celery Task 가 수행한다."""
        if draft_type not in ALLOWED_TYPES:
            raise ValidationError(f"지원하지 않는 글 타입입니다: {draft_type}")
        if audience not in ALLOWED_AUDIENCES:
            raise ValidationError(f"지원하지 않는 독자 유형입니다: {audience}")
        if length_preset not in ALLOWED_LENGTHS:
            raise ValidationError(f"지원하지 않는 길이 설정입니다: {length_preset}")
        if not source_ids:
            raise ValidationError("최소 하나의 소스가 필요합니다.")

        # 남의 소스로 글을 만들 수 없도록 소유권을 확인한다.
        owned = self.source_repo.get_owned_by_ids(user_id, source_ids)
        if len(owned) != len(set(source_ids)):
            raise NotFoundError("존재하지 않거나 접근할 수 없는 소스가 포함되어 있습니다.")

        assert_within_quota(self.job_repo, user_id)

        final_style_profile_id = None
        if use_style_profile and style_profile_id:
            profile = self.style_profile_repo.get_by_id(style_profile_id)
            if not profile or profile.user_id != user_id:
                raise NotFoundError("스타일 프로필을 찾을 수 없습니다.")
            final_style_profile_id = profile.id

        draft = self.draft_repo.create(
            user_id=user_id,
            draft_type=draft_type,
            audience=audience,
            length_preset=length_preset,
            style_profile_id=final_style_profile_id,
        )

        job = self.job_repo.create(
            user_id=user_id,
            job_type=JobType.DRAFT,
            result_ref={"draft_id": draft.id, "source_ids": list(source_ids)},
        )

        return {"id": draft.id, "job_id": job.id, "status": job.status.value}
