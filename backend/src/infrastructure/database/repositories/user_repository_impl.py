import uuid
from typing import List, Optional

from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from src.infrastructure.database.models.user import User
from src.ports.output.repositories.user_repository import UserRepository


def _adjust(column, delta: int):
    """카운터를 delta 만큼 옮기되 0 아래로 내려가지 않게 한다 (SQLite/MariaDB 공통)."""
    if delta >= 0:
        return column + delta
    return case((column + delta > 0, column + delta), else_=0)


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
            # 화면에 보이는 이름은 별도로 둔다. 가입 시에는 가입명을 그대로 쓴다.
            display_name=(name or "")[:60] or None,
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

    # --- 블로그 신원 -------------------------------------------------------

    def get_by_handle(self, handle: str) -> Optional[User]:
        if not handle:
            return None
        return self.db.query(User).filter(User.handle == handle.lower()).first()

    def handle_taken(self, handle: str, exclude_user_id: Optional[str] = None) -> bool:
        q = self.db.query(User.id).filter(User.handle == handle.lower())
        if exclude_user_id:
            q = q.filter(User.id != exclude_user_id)
        return q.first() is not None

    def update_profile(
        self,
        user_id: str,
        handle: Optional[str] = None,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        user = self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if handle is not None:
            user.handle = handle.lower()
        if display_name is not None:
            user.display_name = display_name[:60]
        if bio is not None:
            user.bio = bio
        if avatar_url is not None:
            user.avatar_url = avatar_url

        self.db.commit()
        self.db.refresh(user)
        return user

    def adjust_post_count(self, user_id: str, delta: int) -> None:
        self.db.query(User).filter(User.id == user_id).update(
            {User.post_count: _adjust(User.post_count, delta)}, synchronize_session=False
        )
        self.db.commit()

    def search(self, query: str, limit: int) -> List[User]:
        like = f"%{query.strip()}%"
        return (
            self.db.query(User)
            .filter(
                User.handle.isnot(None),
                or_(User.handle.like(like), User.display_name.like(like)),
            )
            .order_by(User.follower_count.desc())
            .limit(limit)
            .all()
        )
