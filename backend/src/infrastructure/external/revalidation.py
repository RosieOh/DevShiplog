"""프론트엔드 공개 페이지 캐시 무효화 통지.

공개 글은 Next 서버에서 렌더·캐시된다(그래야 검색 크롤러가 읽는다).
따라서 발행·댓글 같은 쓰기가 일어나면 누군가 캐시를 깨야 한다.

브라우저가 알려주도록 두면, 브라우저를 거치지 않는 경로(모바일 앱, CLI, 배치)에서
캐시가 영원히 낡는다. 그래서 쓰기를 실제로 수행하는 백엔드가 알린다.

통지 실패는 절대 본 작업을 실패시키지 않는다. 캐시가 안 깨지면 시간 기반
재검증이 결국 따라잡을 뿐이다.
"""

import json
import logging
import time
from typing import Iterable, List, Optional

import httpx

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 3.0

# Next 인스턴스가 구독하는 채널. 인스턴스가 몇 대든 각자 자기 캐시를 깬다.
CHANNEL = "devshiplog:revalidate"

# 재사용하는 발행 클라이언트. 실패하면 None 으로 되돌려 다음에 새로 만든다.
_client = None
# Redis 가 죽었을 때 매 요청마다 연결 타임아웃을 기다리지 않기 위한 차단기.
# 이 시각까지는 시도 자체를 건너뛴다.
_skip_until = 0.0
BREAKER_SECONDS = 30.0


def tags_for_post(handle: Optional[str], slug: Optional[str]) -> List[str]:
    tags = ["feed"]
    if handle:
        tags.append(f"blog:{handle}")
        if slug:
            tags.append(f"post:{handle}:{slug}")
    return tags


def _redis_client():
    """발행용 Redis 클라이언트. 한 번 만들어 재사용한다.

    호출마다 새로 만들면 연결이 매번 새로 열리고, Redis 가 죽었을 때는
    호출마다 연결 타임아웃을 통째로 기다린다.
    """
    global _client
    if _client is None:
        import redis  # noqa: PLC0415

        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            # 캐시를 깨라는 통지일 뿐이다. 몇 초를 기다릴 가치가 없다.
            # connect 타임아웃을 안 주면 OS 기본값(수십 초)까지 매달린다.
            socket_connect_timeout=1,
            socket_timeout=1,
            health_check_interval=30,
        )
    return _client


def _publish(tag_list: List[str]) -> bool:
    """Redis 로 팬아웃한다. 성공하면 True.

    HTTP 로 한 곳만 때리면 Next 를 여러 대 띄웠을 때 그 한 대만 캐시가 갱신되고
    나머지는 낡은 글을 계속 내보낸다. 발행자는 어떤 인스턴스가 몇 대인지 모른다.
    """
    global _client, _skip_until

    # 방금 실패했다면 잠시 시도하지 않는다. 안 그러면 Redis 가 죽어 있는 동안
    # 발행·댓글 하나하나가 연결 타임아웃만큼 느려진다.
    if time.monotonic() < _skip_until:
        return False

    try:
        _redis_client().publish(CHANNEL, json.dumps({"tags": tag_list}))
        return True
    except Exception:
        # 끊긴 연결을 계속 붙들고 있지 않는다. 다음 호출에서 새로 만든다.
        _client = None
        _skip_until = time.monotonic() + BREAKER_SECONDS
        logger.warning("캐시 무효화 발행 실패 — %.0f초간 HTTP 통지로 대체합니다", BREAKER_SECONDS)
        return False


def notify(tags: Iterable[str]) -> None:
    """Next 에 캐시 무효화를 요청한다. 예외를 밖으로 내보내지 않는다."""
    tag_list = [t for t in tags if t]
    if not tag_list:
        return

    # Redis 가 살아 있으면 그걸로 끝. 실패하면 단일 인스턴스용 HTTP 통지로 내려간다.
    if _publish(tag_list):
        return

    if not settings.FRONTEND_ORIGIN or not settings.REVALIDATE_SECRET:
        # 로컬/테스트에서는 설정하지 않고 쓸 수 있어야 한다.
        return

    url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/api/revalidate"
    try:
        response = httpx.post(
            url,
            json={"tags": tag_list},
            headers={"X-Revalidate-Secret": settings.REVALIDATE_SECRET},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logger.warning("캐시 무효화 실패 (%s): %s", response.status_code, response.text[:200])
    except Exception:
        logger.warning("캐시 무효화 요청 실패 — 시간 기반 재검증으로 대체됩니다", exc_info=False)
