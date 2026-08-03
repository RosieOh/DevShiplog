from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

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
