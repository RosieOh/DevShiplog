from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from ports.input.api.v1.dependencies import get_db
from ports.input.api.v1.auth import get_current_user_id
from infrastructure.database.models.schedule import Schedule, ScheduleStatus

router = APIRouter()


class CreateScheduleRequest(BaseModel):
    draft_id: str
    platform: str  # wordpress, notion, medium
    scheduled_at: str  # ISO datetime string


class ScheduleResponse(BaseModel):
    id: str
    draft_id: str
    platform: str
    scheduled_at: str
    status: str
    created_at: str


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    request: CreateScheduleRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """발행 일정 생성"""
    schedule = Schedule(
        user_id=user_id,
        draft_id=request.draft_id,
        platform=request.platform,
        scheduled_at=datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00')),
        status=ScheduleStatus.PENDING,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return {
        "id": schedule.id,
        "draft_id": schedule.draft_id,
        "platform": schedule.platform,
        "scheduled_at": schedule.scheduled_at.isoformat() if schedule.scheduled_at else "",
        "status": schedule.status.value,
        "created_at": schedule.created_at.isoformat() if schedule.created_at else "",
    }


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """발행 일정 목록 조회"""
    schedules = db.query(Schedule).filter(Schedule.user_id == user_id).order_by(Schedule.scheduled_at.desc()).all()
    
    return [
        {
            "id": s.id,
            "draft_id": s.draft_id,
            "platform": s.platform,
            "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else "",
            "status": s.status.value,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in schedules
    ]


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """발행 일정 삭제"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    db.delete(schedule)
    db.commit()
    
    return {"message": "Schedule deleted successfully"}

