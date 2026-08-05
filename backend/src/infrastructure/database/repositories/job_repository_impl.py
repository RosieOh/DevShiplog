import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.enums import JobStatus, JobType
from src.infrastructure.database.models.job import Job
from src.ports.output.repositories.job_repository import JobRepository


class JobRepositoryImpl(JobRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: str,
        job_type: JobType,
        status: JobStatus = JobStatus.QUEUED,
        result_ref: Optional[dict] = None,
    ) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=job_type,
            status=status,
            progress=0,
            result_ref=result_ref,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: str) -> Optional[Job]:
        # SSE 폴링처럼 같은 세션으로 반복 조회하는 경우 identity map 때문에
        # 다른 프로세스(Celery)가 갱신한 값이 보이지 않는다. 항상 DB 값을 다시 읽는다.
        return (
            self.db.query(Job)
            .populate_existing()
            .filter(Job.id == job_id)
            .first()
        )

    def update_status(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        steps: Optional[dict] = None,
        result_ref: Optional[dict] = None,
        error_text: Optional[str] = None,
    ) -> Job:
        job = self.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if current_step is not None:
            job.current_step = current_step
        if steps is not None:
            job.steps = steps
        if result_ref is not None:
            # JSON 컬럼은 in-place 변경을 감지하지 못하므로 항상 새 dict 를 할당한다.
            job.result_ref = {**(job.result_ref or {}), **result_ref}
        if error_text is not None:
            job.error_text = error_text

        self.db.commit()
        self.db.refresh(job)
        return job

    def count_since(self, user_id: str, since: datetime) -> int:
        return (
            self.db.query(func.count(Job.id))
            .filter(Job.user_id == user_id, Job.created_at >= since)
            .scalar()
            or 0
        )
