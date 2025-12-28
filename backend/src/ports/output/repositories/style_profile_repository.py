from abc import ABC, abstractmethod
from typing import Optional, List
from infrastructure.database.models.style_profile import StyleProfile


class StyleProfileRepository(ABC):
    @abstractmethod
    async def create(self, user_id: str, blog_url: str, sample_count: int = 5) -> StyleProfile:
        pass

    @abstractmethod
    async def get_by_id(self, profile_id: str) -> Optional[StyleProfile]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> List[StyleProfile]:
        pass

    @abstractmethod
    async def update(self, profile: StyleProfile) -> StyleProfile:
        pass

