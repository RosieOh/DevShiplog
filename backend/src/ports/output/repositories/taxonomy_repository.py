from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Sequence

if TYPE_CHECKING:
    from src.infrastructure.database.models.series import Series
    from src.infrastructure.database.models.tag import Tag


class TagRepository(ABC):
    @abstractmethod
    def set_for_post(self, post_id: str, tag_names: Sequence[str]) -> List["Tag"]:
        """글의 태그를 통째로 교체하고 태그별 글 수를 맞춘다."""
        ...

    @abstractmethod
    def list_for_post(self, post_id: str) -> List["Tag"]:
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional["Tag"]:
        ...

    @abstractmethod
    def list_popular(self, limit: int) -> List["Tag"]:
        ...

    @abstractmethod
    def clear_for_post(self, post_id: str) -> None:
        ...


class SeriesRepository(ABC):
    @abstractmethod
    def create(self, user_id: str, slug: str, name: str, description: str = "") -> "Series":
        ...

    @abstractmethod
    def get_by_id(self, series_id: str) -> Optional["Series"]:
        ...

    @abstractmethod
    def get_public(self, handle: str, slug: str) -> Optional["Series"]:
        ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List["Series"]:
        ...

    @abstractmethod
    def slugs_for_user(self, user_id: str) -> List[str]:
        ...

    @abstractmethod
    def add_post(self, series_id: str, post_id: str) -> None:
        ...

    @abstractmethod
    def remove_post(self, series_id: str, post_id: str) -> None:
        ...
