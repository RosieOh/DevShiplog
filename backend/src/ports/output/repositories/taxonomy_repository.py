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

    @abstractmethod
    def context_for_post(self, post_id: str) -> Optional[dict]:
        """이 글이 속한 시리즈와 앞뒤 글. 시리즈에 없으면 None."""

    @abstractmethod
    def reorder(self, series_id: str, post_ids: List[str]) -> None:
        """주어진 순서대로 position 을 다시 매긴다. 빠진 글은 뒤로 밀린다."""

    @abstractmethod
    def delete(self, series_id: str) -> None:
        """시리즈만 지운다. 안에 있던 글은 남는다."""
