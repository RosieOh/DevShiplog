from abc import ABC, abstractmethod
from typing import Optional, List
from infrastructure.database.models.draft import Draft
from infrastructure.database.models.draft_version import DraftVersion


class DraftRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: str,
        draft_type: str,
        audience: str,
        length_preset: str,
        style_profile_id: Optional[str] = None,
    ) -> Draft:
        pass

    @abstractmethod
    async def get_by_id(self, draft_id: str) -> Optional[Draft]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> List[Draft]:
        pass

    @abstractmethod
    async def create_version(
        self,
        draft_id: str,
        version_no: int,
        content_md: str,
        meta_json: dict = None,
    ) -> DraftVersion:
        pass

    @abstractmethod
    async def get_latest_version(self, draft_id: str) -> Optional[DraftVersion]:
        pass

    @abstractmethod
    async def get_versions(self, draft_id: str) -> List[DraftVersion]:
        pass

