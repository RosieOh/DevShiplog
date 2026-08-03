from typing import Any, Dict
from urllib.parse import urlparse

from src.application.errors import ValidationError
from src.application.services.quota import assert_within_quota
from src.domain.enums import JobType
from src.ports.output.repositories.job_repository import JobRepository
from src.ports.output.repositories.style_profile_repository import StyleProfileRepository

MIN_SAMPLES = 1
MAX_SAMPLES = 10


class CreateStyleProfileUseCase:
    def __init__(
        self,
        style_profile_repo: StyleProfileRepository,
        job_repo: JobRepository,
    ):
        self.style_profile_repo = style_profile_repo
        self.job_repo = job_repo

    def execute(self, user_id: str, blog_url: str, sample_count: int = 5) -> Dict[str, Any]:
        """Style DNA 생성 요청. 실제 분석은 Celery Task 가 수행한다."""
        if not (MIN_SAMPLES <= sample_count <= MAX_SAMPLES):
            raise ValidationError(f"샘플 수는 {MIN_SAMPLES}~{MAX_SAMPLES} 사이여야 합니다.")

        # 형식 검증만 여기서 한다. 사설 대역 차단(SSRF)은 실제 요청 시점에
        # infrastructure 의 net_guard 가 담당한다.
        parsed = urlparse(blog_url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValidationError("http(s) 로 시작하는 올바른 블로그 주소를 입력해주세요.")

        # 스타일 분석도 LLM 비용이 발생하므로 동일한 쿼터를 적용한다.
        assert_within_quota(self.job_repo, user_id)

        profile = self.style_profile_repo.create(user_id, blog_url.strip(), sample_count)
        self.job_repo.create(
            user_id=user_id,
            job_type=JobType.STYLE,
            result_ref={"style_profile_id": profile.id},
        )

        return {
            "id": profile.id,
            "status": profile.status.value,
            "blog_url": profile.blog_url,
            "sample_count": profile.sample_count,
        }
