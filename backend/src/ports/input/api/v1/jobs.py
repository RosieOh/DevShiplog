from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from ports.input.api.v1.dependencies import get_job_repo
from ports.input.api.v1.auth import get_current_user_id
from ports.output.repositories.job_repository import JobRepository
import json
import asyncio

router = APIRouter()


class JobResponse(BaseModel):
    id: str
    status: str  # queued, running, succeeded, failed
    progress: int
    current_step: Optional[str] = None
    steps: Optional[dict] = None
    result_ref: Optional[dict] = None
    error_text: Optional[str] = None


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Job 상태 조회"""
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {
        "id": job.id,
        "status": job.status.value,
        "progress": job.progress,
        "current_step": job.current_step,
        "steps": job.steps,
        "result_ref": job.result_ref,
        "error_text": job.error_text,
    }


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Job 스트리밍 (SSE)"""
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    async def event_generator():
        last_progress = 0
        while True:
            job = await job_repo.get_by_id(job_id)
            if not job:
                break
            
            # 진행률이 변경되었거나 새 콘텐츠가 있으면 전송
            if job.progress > last_progress:
                # result_ref에서 콘텐츠 추출 (실제 구현은 Celery task에서 설정)
                content_chunk = ""
                if job.result_ref and "content_chunk" in job.result_ref:
                    content_chunk = job.result_ref.get("content_chunk", "")
                
                yield f"data: {json.dumps({'type': 'chunk', 'content': content_chunk, 'progress': job.progress})}\n\n"
                last_progress = job.progress
            
            if job.status.value == "succeeded":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            elif job.status.value == "failed":
                yield f"data: {json.dumps({'type': 'error', 'message': job.error_text})}\n\n"
                break
            
            await asyncio.sleep(0.5)  # 0.5초마다 체크
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
