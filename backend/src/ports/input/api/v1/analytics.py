"""내 작성 통계 (인증 필요).

집계는 SQL 에서 한다. 초안을 전부 메모리로 읽어 파이썬에서 세면 글이 늘수록
요청 하나가 테이블 전체를 읽는다.
"""

from typing import Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.infrastructure.database.models.draft import Draft
from src.infrastructure.database.models.draft_version import DraftVersion
from src.infrastructure.database.session import get_db
from src.ports.input.api.v1.dependencies import get_current_user_id

router = APIRouter()

UNKNOWN = "unknown"


class DraftStatsResponse(BaseModel):
    total: int
    by_type: Dict[str, int]
    by_audience: Dict[str, int]
    # 실제 본문 글자 수의 평균. 초안이 없으면 0.
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


def _count_by(db: Session, user_id: str, column) -> Dict[str, int]:
    rows = (
        db.query(column, func.count())
        .filter(Draft.user_id == user_id)
        .group_by(column)
        .all()
    )
    return {(value or UNKNOWN): count for value, count in rows}


@router.get("/drafts", response_model=DraftStatsResponse)
def get_draft_stats(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """유형·독자 분포와 평균 길이."""
    total = db.query(func.count(Draft.id)).filter(Draft.user_id == user_id).scalar() or 0
    if total == 0:
        return {
            "total": 0,
            "by_type": {},
            "by_audience": {},
            "average_length": 0.0,
            "style_profile_usage_rate": 0.0,
        }

    with_profile = (
        db.query(func.count(Draft.id))
        .filter(Draft.user_id == user_id, Draft.style_profile_id.isnot(None))
        .scalar()
        or 0
    )

    # 길이는 프리셋이 아니라 실제로 쓴 글자 수로 센다.
    # 프리셋은 "얼마나 쓰려 했는가" 지 "얼마나 썼는가" 가 아니다.
    latest = (
        db.query(
            DraftVersion.draft_id.label("draft_id"),
            func.max(DraftVersion.version_no).label("version_no"),
        )
        .join(Draft, Draft.id == DraftVersion.draft_id)
        .filter(Draft.user_id == user_id)
        .group_by(DraftVersion.draft_id)
        .subquery()
    )
    average_length = (
        db.query(func.avg(func.length(DraftVersion.content_md)))
        .join(
            latest,
            (DraftVersion.draft_id == latest.c.draft_id)
            & (DraftVersion.version_no == latest.c.version_no),
        )
        .scalar()
    )

    return {
        "total": total,
        "by_type": _count_by(db, user_id, Draft.type),
        "by_audience": _count_by(db, user_id, Draft.audience),
        "average_length": round(float(average_length or 0), 1),
        "style_profile_usage_rate": round(with_profile / total * 100, 1),
    }


@router.get("/writing-patterns", response_model=WritingPatternResponse)
def get_writing_patterns(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """가장 많이 쓴 유형·독자·길이."""
    by_type = _count_by(db, user_id, Draft.type)
    by_audience = _count_by(db, user_id, Draft.audience)
    by_length = _count_by(db, user_id, Draft.length_preset)

    def top(counts: Dict[str, int]) -> str:
        return max(counts.items(), key=lambda kv: kv[1])[0] if counts else "none"

    with_profile = (
        db.query(func.count(Draft.id))
        .filter(Draft.user_id == user_id, Draft.style_profile_id.isnot(None))
        .scalar()
        or 0
    )

    return {
        "most_used_type": top(by_type),
        "most_used_audience": top(by_audience),
        "preferred_length": top(by_length),
        "style_profile_usage_count": with_profile,
    }


@router.get("/time-distribution", response_model=TimeDistributionResponse)
def get_time_distribution(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """언제 쓰는가.

    시각은 UTC 기준이다. 사용자의 현지 시각으로 보여주려면 화면에서 옮겨야 한다 —
    여기서 서버 타임존을 쓰면 배포 환경에 따라 값이 달라진다.
    """
    rows = (
        db.query(Draft.created_at)
        .filter(Draft.user_id == user_id, Draft.created_at.isnot(None))
        .all()
    )

    by_hour: Dict[str, int] = {}
    by_day: Dict[str, int] = {}
    for (created_at,) in rows:
        hour = str(created_at.hour)
        day = created_at.strftime("%A")
        by_hour[hour] = by_hour.get(hour, 0) + 1
        by_day[day] = by_day.get(day, 0) + 1

    return {"by_hour": by_hour, "by_day_of_week": by_day}
