"""비밀번호 재설정.

토큰은 원문을 저장하지 않는다. 그 순간 비밀번호와 같은 힘을 가지므로
비밀번호와 같은 취급을 해야 한다 — DB 가 새도 계정을 잡을 수 없어야 한다.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.application.errors import ValidationError
from src.infrastructure.auth.jwt_handler import get_password_hash
from src.infrastructure.config.settings import settings
from src.infrastructure.database.models.password_reset import PasswordResetToken
from src.ports.output.repositories.user_repository import UserRepository

MIN_PASSWORD_LENGTH = 8


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RequestPasswordResetUseCase:
    def __init__(self, db: Session, user_repo: UserRepository):
        self.db = db
        self.user_repo = user_repo

    def execute(self, email: str) -> Optional[str]:
        """토큰 원문을 돌려준다. 계정이 없으면 None.

        호출부는 None 이든 아니든 같은 응답을 내야 한다. 응답이 갈리면
        "이 이메일이 가입되어 있는가" 를 확인하는 도구가 된다.
        """
        user = self.user_repo.get_by_email((email or "").lower())
        if not user:
            return None

        # 이전에 발급한 미사용 토큰은 무효화한다. 하나만 살아 있어야 한다.
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: _now()}, synchronize_session=False)

        token = secrets.token_urlsafe(32)
        self.db.add(
            PasswordResetToken(
                id=str(uuid.uuid4()),
                user_id=user.id,
                token_hash=_hash(token),
                expires_at=_now() + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
            )
        )
        self.db.commit()
        return token


class ConfirmPasswordResetUseCase:
    def __init__(self, db: Session, user_repo: UserRepository):
        self.db = db
        self.user_repo = user_repo

    def execute(self, token: str, new_password: str) -> None:
        if len(new_password or "") < MIN_PASSWORD_LENGTH:
            raise ValidationError(f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.")

        row = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == _hash(token or ""))
            .one_or_none()
        )
        # 만료·재사용·위조를 한 문장으로 묶는다. 어느 쪽인지 알려줄 이유가 없다.
        if not row or row.used_at is not None or row.expires_at <= _now():
            raise ValidationError("링크가 만료되었거나 이미 사용되었습니다.")

        user = self.user_repo.get_by_id(row.user_id)
        if not user:
            raise ValidationError("링크가 만료되었거나 이미 사용되었습니다.")

        user.password_hash = get_password_hash(new_password)
        row.used_at = _now()
        self.db.commit()
