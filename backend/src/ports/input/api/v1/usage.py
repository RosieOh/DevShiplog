from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
from ports.input.api.v1.dependencies import get_db
from ports.input.api.v1.auth import get_current_user_id
from sqlalchemy.orm import Session
from sqlalchemy import func
from infrastructure.database.models.usage_log import UsageLog

router = APIRouter()


class UsageStatsResponse(BaseModel):
    this_month: int
    this_week: int
    total: int


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """사용량 통계 조회"""
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 이번 달 사용량
    this_month_count = db.query(func.count(UsageLog.id)).filter(
        UsageLog.user_id == user_id,
        UsageLog.created_at >= start_of_month
    ).scalar() or 0
    
    # 이번 주 사용량
    this_week_count = db.query(func.count(UsageLog.id)).filter(
        UsageLog.user_id == user_id,
        UsageLog.created_at >= start_of_week
    ).scalar() or 0
    
    # 전체 사용량
    total_count = db.query(func.count(UsageLog.id)).filter(
        UsageLog.user_id == user_id
    ).scalar() or 0
    
    return {
        "this_month": this_month_count,
        "this_week": this_week_count,
        "total": total_count,
    }

