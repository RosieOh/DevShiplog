import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.sql import func

from src.infrastructure.database.session import Base

__all__ = ["ProductEvent"]


class ProductEvent(Base):
    """제품 판단에 필요한 최소 이벤트.

    왜 필요한가: 신선도 기능이 실제로 값어치가 있는지 아직 모른다.
    "쓸 만해 보인다" 는 판단 근거가 아니다. 접을지 말지를 정하려면 수가 있어야 한다.

    범용 분석 도구가 아니다. `docs/PRODUCT_STRATEGY.md` 에 적은 세 가지 질문에
    답하는 데 필요한 것만 담는다.

      1. 자동 추출이 쓸 만한가          → stack_suggested / stack_confirmed
      2. 갱신 루프가 도는가              → post_verified (두 번째부터가 진짜)
      3. 독자 신호가 작성자를 움직이는가  → signal_sent → post_verified 리드타임

    개인정보를 담지 않는다. user_id 는 "같은 사람인가" 판단용이고,
    payload 에는 수치와 분류만 넣는다 — 본문이나 이메일은 넣지 않는다.
    """

    __tablename__ = "product_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 이벤트 이름을 enum 으로 막지 않는다. 새 질문이 생길 때마다 마이그레이션을
    # 돌려야 하면 계측을 안 하게 되고, 그러면 계측이 없는 것과 같다.
    name = Column(String(40), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    payload = Column(JSON)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        # 지표 질의는 항상 "이 이벤트를 이 기간에" 형태다.
        Index("ix_product_events_name_time", "name", "created_at"),
        # 신호 → 검증 리드타임처럼 글 단위로 이어붙이는 질의.
        Index("ix_product_events_post", "post_id", "name"),
    )
