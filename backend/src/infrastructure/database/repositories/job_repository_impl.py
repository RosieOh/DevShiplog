from typing import Optional
from sqlalchemy.orm import Session
from infrastructure.database.models.job import Job, JobType, JobStatus
from ports.output.repositories.job_repository import JobRepository
import uuid


class JobRepositoryImpl(JobRepository):
    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        user_id: str,
        job_type: JobType,
        status: JobStatus = JobStatus.QUEUED,
    ) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=job_type,
            status=status,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        return self.db.query(Job).filter(Job.id == job_id).first()

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: int = None,
        result_ref: dict = None,
        error_text: str = None,
    ) -> Job:
        job = await self.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = status
        if progress is not None:
            job.progress = progress
        if result_ref is not None:
            job.result_ref = result_ref
        if error_text is not None:
            job.error_text = error_text
        
        self.db.commit()
        self.db.refresh(job)
        return job

