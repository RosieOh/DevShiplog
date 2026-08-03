"""Redis 고정 윈도우 레이트리밋.

공개 UGC(댓글·신고·팔로우)와 계정 생성은 열리는 순간 자동화 트래픽이 들어온다.
정교한 알고리즘보다 "있는가"가 훨씬 중요하므로 고정 윈도우로 단순하게 간다.

Redis 에 붙지 못하면 통과시킨다. 레이트리밋 저장소 장애로 서비스 전체가
멈추는 쪽이 더 나쁘기 때문이다 (fail-open).
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import redis

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rule:
    limit: int
    window_seconds: int


# 화면 하나당 정상 사용자가 낼 수 있는 최대치보다 넉넉하되, 자동화는 걸리는 수준
RULES = {
    "comment": Rule(limit=10, window_seconds=60),
    "post_publish": Rule(limit=20, window_seconds=3600),
    "follow": Rule(limit=60, window_seconds=3600),
    "like": Rule(limit=120, window_seconds=60),
    "report": Rule(limit=20, window_seconds=3600),
    "signup": Rule(limit=10, window_seconds=3600),
    "login": Rule(limit=20, window_seconds=300),
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimiter:
    def __init__(self, client: Optional["redis.Redis"] = None):
        self._client = client
        self._checked = client is not None

    @property
    def client(self) -> Optional["redis.Redis"]:
        if not self._checked:
            self._checked = True
            try:
                self._client = redis.Redis.from_url(
                    settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
                )
                self._client.ping()
            except Exception:
                logger.warning("레이트리밋용 Redis 연결 실패 — 제한 없이 통과시킵니다")
                self._client = None
        return self._client

    def check(self, action: str, identity: str) -> Decision:
        rule = RULES.get(action)
        client = self.client
        if rule is None or client is None:
            return Decision(True, -1, 0)

        window = int(time.time()) // rule.window_seconds
        key = f"rl:{action}:{identity}:{window}"

        try:
            pipe = client.pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, rule.window_seconds)
            count = pipe.execute()[0]
        except Exception:
            logger.warning("레이트리밋 조회 실패 (%s) — 통과", action, exc_info=False)
            return Decision(True, -1, 0)

        if count > rule.limit:
            elapsed = int(time.time()) % rule.window_seconds
            return Decision(False, 0, rule.window_seconds - elapsed)
        return Decision(True, rule.limit - count, 0)


rate_limiter = RateLimiter()
