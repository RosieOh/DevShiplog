from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from ports.input.api.v1.dependencies import get_db
from ports.input.api.v1.auth import get_current_user_id
from infrastructure.database.models.draft import Draft
from infrastructure.database.models.usage_log import UsageLog

router = APIRouter()


class DraftStatsResponse(BaseModel):
    total: int
    by_type: Dict[str, int]
    by_audience: Dict[str, int]
    average_length: float
    style_profile_usage_rate: float


class WritingPatternResponse(BaseModel):
    most_used_type: str
    most_used_audience: str
    preferred_length: str
    style_profile_usage_count: int


class TimeDistributionResponse(BaseModel):
    by_hour: Dict[str, int]
    by_day_of_week: Dict[str, int]


@router.get("/drafts", response_model=DraftStatsResponse)
async def get_draft_stats(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Draft 통계"""
    drafts = db.query(Draft).filter(Draft.user_id == user_id).all()
    
    total = len(drafts)
    by_type = {}
    by_audience = {}
    style_profile_count = 0
    
    for draft in drafts:
        by_type[draft.type or "unknown"] = by_type.get(draft.type or "unknown", 0) + 1
        by_audience[draft.audience or "unknown"] = by_audience.get(draft.audience or "unknown", 0) + 1
        if draft.style_profile_id:
            style_profile_count += 1
    
    # 평균 길이 계산 (간단히 타입별로 추정)
    length_map = {"short": 800, "default": 2000, "long": 4000}
    total_length = sum(length_map.get(d.length_preset or "default", 2000) for d in drafts)
    average_length = total_length / total if total > 0 else 0
    
    style_profile_usage_rate = (style_profile_count / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "by_type": by_type,
        "by_audience": by_audience,
        "average_length": average_length,
        "style_profile_usage_rate": style_profile_usage_rate,
    }


@router.get("/writing-patterns", response_model=WritingPatternResponse)
async def get_writing_patterns(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """작성 패턴 분석"""
    drafts = db.query(Draft).filter(Draft.user_id == user_id).all()
    
    if not drafts:
        return {
            "most_used_type": "none",
            "most_used_audience": "none",
            "preferred_length": "none",
            "style_profile_usage_count": 0,
        }
    
    type_counts = {}
    audience_counts = {}
    length_counts = {}
    style_profile_count = 0
    
    for draft in drafts:
        type_counts[draft.type or "unknown"] = type_counts.get(draft.type or "unknown", 0) + 1
        audience_counts[draft.audience or "unknown"] = audience_counts.get(draft.audience or "unknown", 0) + 1
        length_counts[draft.length_preset or "default"] = length_counts.get(draft.length_preset or "default", 0) + 1
        if draft.style_profile_id:
            style_profile_count += 1
    
    most_used_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "none"
    most_used_audience = max(audience_counts.items(), key=lambda x: x[1])[0] if audience_counts else "none"
    preferred_length = max(length_counts.items(), key=lambda x: x[1])[0] if length_counts else "none"
    
    return {
        "most_used_type": most_used_type,
        "most_used_audience": most_used_audience,
        "preferred_length": preferred_length,
        "style_profile_usage_count": style_profile_count,
    }


@router.get("/time-distribution", response_model=TimeDistributionResponse)
async def get_time_distribution(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """시간대별 분포"""
    drafts = db.query(Draft).filter(Draft.user_id == user_id).all()
    
    by_hour = {}
    by_day = {}
    
    for draft in drafts:
        if draft.created_at:
            hour = draft.created_at.hour
            day = draft.created_at.strftime("%A")
            
            by_hour[str(hour)] = by_hour.get(str(hour), 0) + 1
            by_day[day] = by_day.get(day, 0) + 1
    
    return {
        "by_hour": by_hour,
        "by_day_of_week": by_day,
    }

