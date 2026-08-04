import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.sql import func

from src.infrastructure.database.session import Base

__all__ = ["PasswordResetToken"]


class PasswordResetToken(Base):
    """비밀번호 재설정 토큰.

    원문이 아니라 해시를 저장한다. DB 가 새어도 토큰으로 남의 계정을 못 잡게 하려면
    비밀번호와 같은 취급을 해야 한다 — 토큰은 그 순간 비밀번호와 같은 힘을 가진다.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_password_reset_user", "user_id", "created_at"),)
