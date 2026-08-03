from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from src.domain.enums import SourceType

if TYPE_CHECKING:
    from src.infrastructure.database.models.source import Source


class SourceRepository(ABC):
    @abstractmethod
    def create(
        self,
        user_id: str,
        source_type: SourceType,
        origin: str,
        title: str,
        content: str,
        extracted_json: Optional[dict] = None,
    ) -> "Source":
        ...

    @abstractmethod
    def get_by_id(self, source_id: str) -> Optional["Source"]:
        ...

    @abstractmethod
    def get_by_ids(self, source_ids: List[str]) -> List["Source"]:
        ...

    @abstractmethod
    def get_owned_by_ids(self, user_id: str, source_ids: List[str]) -> List["Source"]:
        """해당 사용자가 소유한 소스만 조회한다."""
        ...
