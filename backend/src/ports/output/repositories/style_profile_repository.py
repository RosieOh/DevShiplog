from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from src.domain.enums import StyleProfileStatus

if TYPE_CHECKING:
    from src.infrastructure.database.models.style_profile import StyleProfile


class StyleProfileRepository(ABC):
    @abstractmethod
    def create(self, user_id: str, blog_url: str, sample_count: int = 5) -> "StyleProfile":
        ...

    @abstractmethod
    def get_by_id(self, profile_id: str) -> Optional["StyleProfile"]:
        ...

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> List["StyleProfile"]:
        ...

    @abstractmethod
    def update_result(
        self,
        profile_id: str,
        status: StyleProfileStatus,
        profile_json: Optional[dict] = None,
        error_text: Optional[str] = None,
    ) -> "StyleProfile":
        ...
