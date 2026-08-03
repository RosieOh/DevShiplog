from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.infrastructure.database.models.usage_log import UsageLog


class UsageLogRepository(ABC):
    @abstractmethod
    def record(
        self,
        user_id: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        job_id: Optional[str] = None,
    ) -> "UsageLog":
        ...

    @abstractmethod
    def count_since(self, user_id: str, since: datetime) -> int:
        ...

    @abstractmethod
    def token_totals_since(self, user_id: str, since: datetime) -> dict:
        """{'prompt_tokens': int, 'completion_tokens': int, 'cost_usd': float}"""
        ...
