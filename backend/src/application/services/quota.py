from datetime import datetime, timezone

from src.application.errors import QuotaExceededError
from src.infrastructure.config.settings import settings
from src.ports.output.repositories.job_repository import JobRepository


def month_start(now: datetime = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


def assert_within_quota(job_repo: JobRepository, user_id: str) -> None:
    """이번 달 Job 생성 한도를 초과했으면 QuotaExceededError.

    LLM 호출은 실제 비용이 나가므로, Job 을 만들기 전에 반드시 검사한다.
    """
    limit = settings.MONTHLY_JOB_QUOTA
    if limit <= 0:  # 0 이면 무제한
        return

    used = job_repo.count_since(user_id, month_start())
    if used >= limit:
        raise QuotaExceededError(
            f"이번 달 생성 한도({limit}건)를 모두 사용했습니다. 다음 달에 다시 시도해주세요."
        )
