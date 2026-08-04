from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from src.domain.enums import RiskStatus

if TYPE_CHECKING:
    from src.infrastructure.database.models.risk_finding import RiskFinding


class RiskFindingRepository(ABC):
    @abstractmethod
    def create(
        self,
        draft_version_id: str,
        category: str,
        severity: str,
        snippet: str,
        location_json: dict,
    ) -> "RiskFinding":
        ...

    @abstractmethod
    def get_by_id(self, finding_id: str) -> Optional["RiskFinding"]:
        ...

    @abstractmethod
    def get_by_draft_version_id(self, draft_version_id: str) -> List["RiskFinding"]:
        ...

    @abstractmethod
    def delete_by_draft_version_id(self, draft_version_id: str) -> int:
        """재스캔 시 기존 결과를 지운다. 삭제된 행 수를 반환."""
        ...

    @abstractmethod
    def update_status(
        self,
        finding_id: str,
        status: RiskStatus,
        ignore_reason: Optional[str] = None,
    ) -> "RiskFinding":
        ...
