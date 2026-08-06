import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.domain.enums import SignalKind
from src.infrastructure.database.session import Base

__all__ = ["PostStack", "PostSignal"]


class PostStack(Base):
    """글이 전제하는 기술과 버전.

    태그와 다르다. 태그는 "무엇에 관한 글인가" 이고, 이건 "어느 환경에서 확인된 절차인가" 다.
    자유 문자열이 아니라 정규화된 이름을 쓴다 — 그래야 "React 18 글 모음" 을 질의할 수 있고,
    그 질의가 이 제품의 핵심이다.
    """

    __tablename__ = "post_stacks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    # domain/services/tech_stack.py 의 ALIASES 로 정규화된 값
    name = Column(String(40), nullable=False)
    # "18.3" 처럼 메이저.마이너까지만. 패치까지 적으면 낡음 판정이 지나치게 민감해진다.
    version = Column(String(20))
    # 자동 추출의 확신도. 작성자에게 무엇을 먼저 확인시킬지 정하는 데 쓴다.
    confidence = Column(String(10), nullable=False, default="high")
    position = Column(Integer, nullable=False, default=0)

    post = relationship("Post", back_populates="stacks")

    __table_args__ = (
        # 같은 글에 같은 스택이 두 번 들어가지 않는다. 버전이 다르면 그건 보정 실수다.
        UniqueConstraint("post_id", "name", name="unique_post_stack"),
        # 스택 탐색 페이지(/stacks/react)의 주 경로.
        Index("ix_post_stacks_name_version", "name", "version"),
    )


class PostSignal(Base):
    """독자가 보내는 "지금도 되나요?" 신호.

    댓글로 받으면 묻힌다. "저도 안 돼요" 가 세 개 달려도 작성자는 모르고,
    설령 봐도 어느 글부터 고쳐야 할지 판단할 수 없다.

    구조화해서 받으면 작성자 대시보드에서 "신호 많은 순" 으로 정렬할 수 있다.
    """

    __tablename__ = "post_signals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    # 로그인한 사람만 보낼 수 있다. 익명으로 열면 경쟁 글을 깎는 데 쓰인다.
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind = Column(Enum(SignalKind), nullable=False)
    # "Node 22 에서는 이 옵션이 없어졌습니다" 같은 한 줄. 없어도 된다.
    note = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    # 작성자가 확인·처리한 시각. 처리하면 목록에서 내려간다.
    resolved_at = Column(DateTime)

    post = relationship("Post", back_populates="signals")
    user = relationship("User")

    __table_args__ = (
        # 한 사람이 한 글에 하나. 여러 번 눌러 신호를 부풀리지 못하게.
        UniqueConstraint("post_id", "user_id", name="unique_post_signal_per_user"),
        Index("ix_post_signals_post_resolved", "post_id", "resolved_at"),
    )
