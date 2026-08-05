"""발행 예약 (인증 필요)."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.application.errors import NotFoundError, ValidationError
from src.infrastructure.database.models.draft import Draft
from src.infrastructure.database.models.schedule import Schedule, ScheduleStatus
from src.infrastructure.database.session import get_db
from src.ports.input.api.v1.dependencies import get_current_user_id

router = APIRouter()

# 아직 실제로 연동한 곳은 없다. 문자열을 자유롭게 받으면 오타가 그대로 저장되고
# 나중에 목록을 만들 때 정리할 수 없게 된다.
PLATFORMS = {"wordpress", "notion", "medium", "devshiplog"}


class CreateScheduleRequest(BaseModel):
    draft_id: str
    platform: str
    # ISO 8601. 타임존이 없으면 UTC 로 본다.
    scheduled_at: str = Field(max_length=40)


class ScheduleResponse(BaseModel):
    id: str
    draft_id: str
    platform: str
    scheduled_at: str
    status: str
    created_at: str


def _payload(schedule: Schedule) -> dict:
    return {
        "id": schedule.id,
        "draft_id": schedule.draft_id,
        "platform": schedule.platform,
        "scheduled_at": schedule.scheduled_at.isoformat() if schedule.scheduled_at else "",
        "status": schedule.status.value,
        "created_at": schedule.created_at.isoformat() if schedule.created_at else "",
    }


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    request: CreateScheduleRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """발행 예약을 만든다."""
    if request.platform not in PLATFORMS:
        raise ValidationError(f"지원하지 않는 플랫폼입니다: {request.platform}")

    try:
        when = datetime.fromisoformat(request.scheduled_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("예약 시각 형식이 올바르지 않습니다 (ISO 8601).") from exc

    # 타임존이 없는 값은 UTC 로 본다. DB 컬럼이 naive 라 저장 전에 벗겨야 한다.
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when <= datetime.now(timezone.utc):
        raise ValidationError("예약 시각은 현재보다 뒤여야 합니다.")

    # draft_id 를 그대로 믿으면 남의 초안을 예약할 수 있다.
    owned = (
        db.query(Draft.id)
        .filter(Draft.id == request.draft_id, Draft.user_id == user_id)
        .first()
    )
    if not owned:
        # 없는 것과 남의 것을 구분하지 않는다. 구분하면 존재 여부가 새어나간다.
        raise NotFoundError("초안을 찾을 수 없습니다.")

    schedule = Schedule(
        user_id=user_id,
        draft_id=request.draft_id,
        platform=request.platform,
        scheduled_at=when.astimezone(timezone.utc).replace(tzinfo=None),
        status=ScheduleStatus.PENDING,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _payload(schedule)


@router.get("", response_model=List[ScheduleResponse])
def list_schedules(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """내 발행 예약 목록."""
    rows = (
        db.query(Schedule)
        .filter(Schedule.user_id == user_id)
        .order_by(Schedule.scheduled_at.desc())
        .all()
    )
    return [_payload(s) for s in rows]


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """예약을 취소한다."""
    # 소유 조건을 조회에 포함한다. 찾은 뒤에 비교하면 "있긴 있다" 를 알려주게 된다.
    schedule = (
        db.query(Schedule)
        .filter(Schedule.id == schedule_id, Schedule.user_id == user_id)
        .first()
    )
    if not schedule:
        raise NotFoundError("예약을 찾을 수 없습니다.")

    db.delete(schedule)
    db.commit()
    return {"deleted": True}
