from abc import ABC, abstractmethod
from typing import List
from infrastructure.database.models.source import Source, SourceType


class SourceRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: str,
        source_type: SourceType,
        origin: str,
        title: str,
        content: str,
        extracted_json: dict = None,
    ) -> Source:
        pass

    @abstractmethod
    async def get_by_id(self, source_id: str) -> Source:
        pass

    @abstractmethod
    async def get_by_ids(self, source_ids: List[str]) -> List[Source]:
        pass

