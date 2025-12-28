from abc import ABC, abstractmethod
from typing import Optional
from infrastructure.database.models.job import Job, JobType, JobStatus


class JobRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: str,
        job_type: JobType,
        status: JobStatus = JobStatus.QUEUED,
    ) -> Job:
        pass

    @abstractmethod
    async def get_by_id(self, job_id: str) -> Optional[Job]:
        pass

    @abstractmethod
    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: int = None,
        current_step: str = None,
        steps: dict = None,
        result_ref: dict = None,
        error_text: str = None,
    ) -> Job:
        pass

