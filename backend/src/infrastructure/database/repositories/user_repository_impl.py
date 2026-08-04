import uuid
from typing import Optional

from sqlalchemy.orm import Session

from src.infrastructure.database.models.user import User
from src.ports.output.repositories.user_repository import UserRepository


class UserRepositoryImpl(UserRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, email: str, name: Optional[str] = None, password_hash: Optional[str] = None
    ) -> User:
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

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        # 이메일은 대소문자를 구분하지 않고 저장/조회한다.
        return self.db.query(User).filter(User.email == email.lower()).first()
