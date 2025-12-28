from typing import Optional
from sqlalchemy.orm import Session
from infrastructure.database.models.user import User
from ports.output.repositories.user_repository import UserRepository
import uuid


class UserRepositoryImpl(UserRepository):
    def __init__(self, db: Session):
        self.db = db

    async def create(self, email: str, name: Optional[str] = None, password_hash: Optional[str] = None) -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            password_hash=password_hash or "",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    async def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

