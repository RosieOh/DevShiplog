from abc import ABC, abstractmethod
from typing import List
from infrastructure.database.models.risk_finding import RiskFinding, RiskStatus


class RiskFindingRepository(ABC):
    @abstractmethod
    async def create(
        self,
        draft_version_id: str,
        category: str,
        severity: str,
        snippet: str,
        location_json: dict,
    ) -> RiskFinding:
        pass

    @abstractmethod
    async def get_by_draft_version_id(self, draft_version_id: str) -> List[RiskFinding]:
        pass

    @abstractmethod
    async def update_status(
        self,
        finding_id: str,
        status: RiskStatus,
        ignore_reason: str = None,
    ) -> RiskFinding:
        pass

