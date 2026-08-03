"""프론트엔드 공개 페이지 캐시 무효화 통지.

공개 글은 Next 서버에서 렌더·캐시된다(그래야 검색 크롤러가 읽는다).
따라서 발행·댓글 같은 쓰기가 일어나면 누군가 캐시를 깨야 한다.

브라우저가 알려주도록 두면, 브라우저를 거치지 않는 경로(모바일 앱, CLI, 배치)에서
캐시가 영원히 낡는다. 그래서 쓰기를 실제로 수행하는 백엔드가 알린다.

통지 실패는 절대 본 작업을 실패시키지 않는다. 캐시가 안 깨지면 시간 기반
재검증이 결국 따라잡을 뿐이다.
"""

import logging
from typing import Iterable, List, Optional

import httpx

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 3.0


def tags_for_post(handle: Optional[str], slug: Optional[str]) -> List[str]:
    tags = ["feed"]
    if handle:
        tags.append(f"blog:{handle}")
        if slug:
            tags.append(f"post:{handle}:{slug}")
    return tags


def notify(tags: Iterable[str]) -> None:
    """Next 에 캐시 무효화를 요청한다. 예외를 밖으로 내보내지 않는다."""
    tag_list = [t for t in tags if t]
    if not tag_list:
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
