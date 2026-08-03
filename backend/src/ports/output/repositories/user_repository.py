from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from src.infrastructure.database.models.user import User


class UserRepository(ABC):
    @abstractmethod
    def create(
        self, email: str, name: Optional[str] = None, password_hash: Optional[str] = None
    ) -> "User":
        ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional["User"]:
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional["User"]:
        ...

    # --- 블로그 신원 -------------------------------------------------------

    @abstractmethod
    def get_by_handle(self, handle: str) -> Optional["User"]:
        ...

    @abstractmethod
    def handle_taken(self, handle: str, exclude_user_id: Optional[str] = None) -> bool:
        ...

    @abstractmethod
    def update_profile(
        self,
        user_id: str,
        handle: Optional[str] = None,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> "User":
        ...

    @abstractmethod
    def adjust_post_count(self, user_id: str, delta: int) -> None:
        ...

    @abstractmethod
    def search(self, query: str, limit: int) -> List["User"]:
        ...
