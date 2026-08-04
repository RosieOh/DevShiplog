"""Celery Task 공통 유틸.

- ProgressWriter: 스트리밍 중간 결과를 Job 에 흘려보내 SSE 가 읽을 수 있게 한다.
- record_usage: LLM 호출 사용량을 UsageLog 로 남긴다.
"""

import logging
import time
from typing import Optional

from src.domain.enums import JobStatus
from src.ports.output.repositories.job_repository import JobRepository
from src.ports.output.repositories.usage_log_repository import UsageLogRepository
from src.ports.output.services.llm_service import LLMUsage

logger = logging.getLogger(__name__)

# DB 쓰기 부하를 줄이기 위한 스트리밍 반영 주기
FLUSH_INTERVAL_SECONDS = 1.0


class ProgressWriter:
    """스트리밍 청크를 모아 주기적으로 Job.result_ref 에 반영한다.

    SSE 엔드포인트는 result_ref["content"] 의 길이를 보고 새로 늘어난 부분만
    클라이언트로 내보낸다.
    """

    def __init__(
        self,
        job_repo: JobRepository,
        job_id: str,
        start_progress: int,
        end_progress: int,
    ):
        self.job_repo = job_repo
        self.job_id = job_id
        self.start_progress = start_progress
        self.end_progress = end_progress
        self._buffer: list[str] = []
        self._last_flush = 0.0

    @property
    def text(self) -> str:
        return "".join(self._buffer)

    def on_chunk(self, chunk: str) -> None:
        self._buffer.append(chunk)
        now = time.monotonic()
        if now - self._last_flush >= FLUSH_INTERVAL_SECONDS:
            self._last_flush = now
            self.flush()

    def flush(self, progress: Optional[int] = None) -> None:
        try:
            self.job_repo.update_status(
                self.job_id,
                status=JobStatus.RUNNING,
                progress=progress if progress is not None else self._estimate_progress(),
                result_ref={"content": self.text},
            )
        except Exception:  # 진행률 반영 실패가 본 작업을 죽이면 안 된다
            logger.warning("진행률 반영 실패 (job=%s)", self.job_id, exc_info=True)

    def _estimate_progress(self) -> int:
        # 목표 길이를 모르므로 2000자를 기준으로 구간 내에서 완만히 증가시킨다.
        span = self.end_progress - self.start_progress
        ratio = min(len(self.text) / 2000.0, 1.0)
        return int(self.start_progress + span * ratio)


def record_usage(
    usage_repo: UsageLogRepository,
    user_id: str,
    job_id: Optional[str],
    usage: Optional[LLMUsage],
) -> None:
    """LLM 사용량을 기록한다. 기록 실패가 본 작업을 죽이지 않도록 감싼다."""
    if usage is None:
        return
    try:
        usage_repo.record(
            user_id=user_id,
            model_name=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost_usd=usage.cost_usd,
            job_id=job_id,
        )
    except Exception:
        logger.warning("사용량 기록 실패 (job=%s)", job_id, exc_info=True)
