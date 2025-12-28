from abc import ABC, abstractmethod
from typing import Optional
from infrastructure.database.models.user import User


class UserRepository(ABC):
    @abstractmethod
    async def create(self, email: str, name: Optional[str] = None, password_hash: Optional[str] = None) -> User:
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

