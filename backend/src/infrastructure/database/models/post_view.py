import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.sql import func

from src.infrastructure.database.session import Base

__all__ = ["PostView"]


class PostView(Base):
    """조회 기록.

    두 가지 일을 한다.
    1) 조회수 중복 제거 — 새로고침할 때마다 오르면 숫자를 믿을 수 없다.
    2) 추천 신호 — 좋아요는 안 눌러도 읽기는 한다. 좋아요보다 훨씬 흔한 신호다.

    로그인하지 않은 독자는 user_id 가 없으므로 viewer_key(IP+UA 해시)로 구분한다.
    IP 를 그대로 저장하지 않는 이유: 개인정보를 남길 이유가 없고, 해시만으로도
    "같은 사람이 다시 왔나" 를 판단하기에 충분하다.
    """

    __tablename__ = "post_views"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    viewer_key = Column(String(64), nullable=False)
    viewed_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        # 같은 글 + 같은 뷰어는 한 행. 재방문은 viewed_at 만 갱신한다.
        UniqueConstraint("post_id", "viewer_key", name="unique_post_viewer"),
        # 추천에서 "내가 최근에 본 글" 을 뽑을 때 쓴다.
        Index("ix_post_views_user_time", "user_id", "viewed_at"),
    )
