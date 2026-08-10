import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from src.infrastructure.database.session import Base

__all__ = ["ErrorGroup"]


class ErrorGroup(Base):
    """서버 오류를 지문별로 묶어 남긴다.

    메모리에만 두었더니 재시작하면 사라지고, 워커가 여럿이면 요청이 닿은 워커의
    것만 보였다. "어제 밤에 뭐가 터졌지" 를 물을 수 없는 기록은 기록이 아니다.

    한 건씩 쌓지 않고 묶는 이유: 같은 오류가 1000번 나면 표가 그것만으로 가득 차서
    무엇부터 고칠지 알 수 없다. 묶어야 "무엇이 몇 번" 이 보인다.

    본문·이메일 같은 개인정보는 담지 않는다. 스택트레이스에 사용자 입력이 섞일 수
    있어서 운영자에게만 보인다.
    """

    __tablename__ = "error_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 예외 타입 + 마지막 우리 코드 위치 + 경로로 만든다. 메시지는 넣지 않는다 —
    # ID 가 섞인 메시지 때문에 같은 버그가 매번 새 그룹이 된다.
    fingerprint = Column(String(32), nullable=False, unique=True)

    type = Column(String(120), nullable=False)
    message = Column(String(300))
    origin = Column(String(500))
    path = Column(String(500))
    method = Column(String(10))
    traceback = Column(Text)

    count = Column(Integer, nullable=False, default=1)
    first_seen = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen = Column(DateTime, server_default=func.now(), nullable=False)
    last_request_id = Column(String(64))

    # 알림을 언제 보냈는지. 이게 없으면 같은 오류로 메일이 1000통 간다.
    notified_at = Column(DateTime)
    # 운영자가 확인 처리한 시각. 지우지 않는다 — 다시 나면 count 가 올라가야 한다.
    resolved_at = Column(DateTime)

    __table_args__ = (
        # 화면은 항상 "최근에 난 것부터" 로 본다.
        Index("ix_error_groups_last_seen", "last_seen"),
        # 미처리만 보는 질의가 기본이다.
        Index("ix_error_groups_resolved_seen", "resolved_at", "last_seen"),
    )
