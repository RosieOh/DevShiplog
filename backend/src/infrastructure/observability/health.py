"""준비 상태.

`{"status": "healthy"}` 만 돌려주는 헬스체크는 프로세스가 살아있다는 것만 말한다.
DB 가 끊겨도 그건 계속 healthy 라고 답하고, 로드밸런서는 죽은 인스턴스로 트래픽을 계속 보낸다.

liveness 와 readiness 를 나눈다.
- /health      : 프로세스가 살아있는가 (재시작 판단)
- /health/ready: 요청을 처리할 수 있는가 (트래픽 투입 판단)
"""

import logging
import time
from typing import Any, Callable, Dict

from sqlalchemy import text

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# 하나가 늦게 답할 때 나머지까지 붙잡고 있으면 헬스체크 자체가 타임아웃된다.
_TIMEOUT_SECONDS = 2


def _timed(name: str, probe: Callable[[], None], *, required: bool) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        probe()
        return {
            "name": name,
            "ok": True,
            "required": required,
            "ms": round((time.perf_counter() - started) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("준비 상태 점검 실패: %s", name, exc_info=True)
        return {
            "name": name,
            "ok": False,
            "required": required,
            "ms": round((time.perf_counter() - started) * 1000, 1),
            # 예외 문자열에 접속 문자열이 통째로 들어오는 경우가 있어 길이를 자른다.
            "error": f"{type(exc).__name__}: {str(exc)[:160]}",
        }


def _check_database() -> None:
    from src.infrastructure.database.session import engine

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _check_redis() -> None:
    import redis

    client = redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=_TIMEOUT_SECONDS,
        socket_timeout=_TIMEOUT_SECONDS,
    )
    try:
        client.ping()
    finally:
        client.close()


def _check_storage() -> None:
    from src.infrastructure.external.storage import get_storage

    storage = get_storage()
    if hasattr(storage, "client"):
        storage.client.head_bucket(Bucket=storage.bucket)


def readiness() -> Dict[str, Any]:
    """의존성을 하나씩 두드려 본다.

    Redis 를 required 로 두지 않는 이유:
    레이트리밋과 캐시 무효화가 Redis 를 쓰지만, 끊겨도 글 읽기와 쓰기는 된다.
    이걸 required 로 두면 Redis 재시작 때 서비스 전체가 트래픽에서 빠진다 —
    실제로는 조금 불편해질 뿐인데.
    """
    checks = [
        _timed("database", _check_database, required=True),
        _timed("redis", _check_redis, required=False),
        _timed("storage", _check_storage, required=settings.STORAGE_BACKEND == "s3"),
    ]
    ready = all(check["ok"] for check in checks if check["required"])
    return {"ready": ready, "checks": checks}
