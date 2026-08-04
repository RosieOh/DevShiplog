import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl
from src.infrastructure.database.session import SessionLocal
from src.ports.input.api.v1.dependencies import (
    get_current_user_id,
    get_current_user_id_sse,
    get_job_repo,
)
from src.ports.output.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)

router = APIRouter()

POLL_INTERVAL_SECONDS = 0.5
# 스트림이 영원히 살아있지 않도록 상한을 둔다 (Celery soft time limit 보다 넉넉히).
MAX_STREAM_SECONDS = 360
# 프록시가 유휴 연결을 끊지 않도록 주기적으로 주석 라인을 보낸다.
HEARTBEAT_SECONDS = 15


class JobResponse(BaseModel):
    id: str
    status: str  # queued, running, succeeded, failed
    progress: int
    result_ref: Optional[Dict[str, Any]] = None
    error_text: Optional[str] = None


def _job_payload(job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status.value,
        "progress": job.progress or 0,
        "result_ref": job.result_ref,
        "error_text": job.error_text,
    }


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    job_repo: JobRepository = Depends(get_job_repo),
):
    """Job 상태 조회"""
    job = job_repo.get_by_id(job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job 을 찾을 수 없습니다.")
    return _job_payload(job)


def _sse(event: Dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.get("/{job_id}/stream")
def stream_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id_sse),
):
    """Job 진행 상황 스트리밍 (SSE).

    Celery 워커가 Job.result_ref["content"] 에 누적해 둔 본문을 읽어
    새로 늘어난 부분만 델타로 내보낸다.

    브라우저 EventSource 는 헤더를 못 붙이므로 `?token=` 으로도 인증을 받는다.
    """

    async def event_generator():
        # 요청 스코프 세션을 오래 붙들지 않도록 스트림 전용 세션을 따로 연다.
        db = SessionLocal()
        job_repo = JobRepositoryImpl(db)
        sent_len = 0
        elapsed = 0.0
        since_heartbeat = 0.0

        try:
            job = job_repo.get_by_id(job_id)
            if not job or job.user_id != user_id:
                yield _sse({"type": "error", "message": "Job 을 찾을 수 없습니다."})
                return

            while elapsed < MAX_STREAM_SECONDS:
                # MySQL 기본 격리수준(REPEATABLE READ)에서는 같은 트랜잭션 안의
                # 반복 조회가 첫 스냅샷을 계속 돌려준다. 매 폴링마다 트랜잭션을
                # 새로 시작해야 워커가 쓴 값이 보인다.
                db.rollback()
                job = job_repo.get_by_id(job_id)
                if not job:
                    yield _sse({"type": "error", "message": "Job 이 사라졌습니다."})
                    return

                content = (job.result_ref or {}).get("content", "") or ""
                if len(content) > sent_len:
                    yield _sse(
                        {
                            "type": "chunk",
                            "content": content[sent_len:],
                            "progress": job.progress or 0,
                        }
                    )
                    sent_len = len(content)
                    since_heartbeat = 0.0

                state = job.status.value
                if state == "succeeded":
                    yield _sse(
                        {
                            "type": "done",
                            "progress": 100,
                            "draft_id": (job.result_ref or {}).get("draft_id"),
                        }
                    )
                    return
                if state == "failed":
                    yield _sse({"type": "error", "message": job.error_text or "작업에 실패했습니다."})
                    return

                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                elapsed += POLL_INTERVAL_SECONDS
                since_heartbeat += POLL_INTERVAL_SECONDS

                if since_heartbeat >= HEARTBEAT_SECONDS:
                    since_heartbeat = 0.0
                    yield ": keep-alive\n\n"

            yield _sse({"type": "error", "message": "시간이 초과되었습니다. 잠시 후 다시 확인해주세요."})
        except asyncio.CancelledError:  # 클라이언트가 연결을 끊은 경우
            raise
        except Exception:
            logger.exception("SSE 스트림 오류 (job=%s)", job_id)
            yield _sse({"type": "error", "message": "스트리밍 중 오류가 발생했습니다."})
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
        },
    )
