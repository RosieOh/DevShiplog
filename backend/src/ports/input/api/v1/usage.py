from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.infrastructure.config.settings import settings
from src.ports.input.api.v1.dependencies import (
    get_current_user_id,
    get_job_repo,
    get_usage_log_repo,
)
from src.ports.output.repositories.job_repository import JobRepository
from src.ports.output.repositories.usage_log_repository import UsageLogRepository

router = APIRouter()


class UsageStatsResponse(BaseModel):
    this_month: int
    this_week: int
    total: int
    monthly_quota: int
    remaining: int
    prompt_tokens_this_month: int
    completion_tokens_this_month: int
    cost_usd_this_month: float


@router.get("/stats", response_model=UsageStatsResponse)
def get_usage_stats(
    user_id: str = Depends(get_current_user_id),
    usage_repo: UsageLogRepository = Depends(get_usage_log_repo),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """사용량 통계 조회.

    호출 건수는 실제 LLM 호출 기록(UsageLog)을 기준으로 하고,
    쿼터 잔여량은 쿼터 계산과 동일하게 Job 수를 기준으로 한다.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    epoch = datetime(1970, 1, 1)

    tokens = usage_repo.token_totals_since(user_id, start_of_month)
    jobs_this_month = job_repo.count_since(user_id, start_of_month)
    quota = settings.MONTHLY_JOB_QUOTA

    return UsageStatsResponse(
        this_month=usage_repo.count_since(user_id, start_of_month),
        this_week=usage_repo.count_since(user_id, start_of_week),
        total=usage_repo.count_since(user_id, epoch),
        monthly_quota=quota,
        remaining=max(quota - jobs_this_month, 0) if quota > 0 else -1,
        prompt_tokens_this_month=tokens["prompt_tokens"],
        completion_tokens_this_month=tokens["completion_tokens"],
        cost_usd_this_month=round(tokens["cost_usd"], 4),
    )
