import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.infrastructure.database.models.usage_log import UsageLog
from src.ports.output.repositories.usage_log_repository import UsageLogRepository


class UsageLogRepositoryImpl(UsageLogRepository):
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        user_id: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        job_id: Optional[str] = None,
    ) -> UsageLog:
        log = UsageLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_id=job_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=Decimal(str(round(cost_usd, 6))),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def count_since(self, user_id: str, since: datetime) -> int:
        return (
            self.db.query(func.count(UsageLog.id))
            .filter(UsageLog.user_id == user_id, UsageLog.created_at >= since)
            .scalar()
            or 0
        )

    def token_totals_since(self, user_id: str, since: datetime) -> dict:
        row = (
            self.db.query(
                func.coalesce(func.sum(UsageLog.prompt_tokens), 0),
                func.coalesce(func.sum(UsageLog.completion_tokens), 0),
                func.coalesce(func.sum(UsageLog.cost_usd), 0),
            )
            .filter(UsageLog.user_id == user_id, UsageLog.created_at >= since)
            .one()
        )
        return {
            "prompt_tokens": int(row[0] or 0),
            "completion_tokens": int(row[1] or 0),
            "cost_usd": float(row[2] or 0),
        }
