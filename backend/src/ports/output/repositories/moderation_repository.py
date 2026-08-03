from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from src.domain.enums import ReportReason, ReportStatus, ReportTargetType

if TYPE_CHECKING:
    from src.infrastructure.database.models.moderation import Report


class ReportRepository(ABC):
    @abstractmethod
    def create(
        self,
        reporter_id: str,
        target_type: ReportTargetType,
        target_id: str,
        reason: ReportReason,
        detail: str = "",
    ) -> Optional["Report"]:
        """같은 대상을 같은 사람이 다시 신고하면 None (큐 도배 방지)."""
        ...

    @abstractmethod
    def count_open_for_target(self, target_type: ReportTargetType, target_id: str) -> int:
        ...

    @abstractmethod
    def list_open(self, limit: int, offset: int) -> List["Report"]:
        ...

    @abstractmethod
    def resolve(self, report_id: str, status: ReportStatus) -> "Report":
        ...


class BlockRepository(ABC):
    @abstractmethod
    def block(self, blocker_id: str, blocked_id: str) -> bool:
        ...

    @abstractmethod
    def unblock(self, blocker_id: str, blocked_id: str) -> bool:
        ...

    @abstractmethod
    def blocked_ids(self, blocker_id: str) -> List[str]:
        """내가 차단한 사람들. 목록/댓글에서 걸러낼 때 쓴다."""
        ...

    @abstractmethod
    def is_blocked(self, blocker_id: str, blocked_id: str) -> bool:
        ...
