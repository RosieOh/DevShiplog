from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from src.domain.enums import JobStatus, JobType

if TYPE_CHECKING:
    from src.infrastructure.database.models.job import Job


class JobRepository(ABC):
    @abstractmethod
    def create(
        self,
        user_id: str,
        job_type: JobType,
        status: JobStatus = JobStatus.QUEUED,
        result_ref: Optional[dict] = None,
    ) -> "Job":
        ...

    @abstractmethod
    def get_by_id(self, job_id: str) -> Optional["Job"]:
        ...

    @abstractmethod
    def update_status(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        # 단계별 진행 상황. 긴 작업에서 "지금 어디쯤인지" 를 보여주기 위한 값이다.
        current_step: Optional[str] = None,
        steps: Optional[dict] = None,
        result_ref: Optional[dict] = None,
        error_text: Optional[str] = None,
    ) -> "Job":
        ...

    @abstractmethod
    def count_since(self, user_id: str, since: datetime) -> int:
        """특정 시각 이후 사용자가 만든 Job 수 (사용량 쿼터 계산용)."""
        ...
