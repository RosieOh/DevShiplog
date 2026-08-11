"""하트비트 (데드맨 스위치).

지금까지의 알림은 전부 **앱이 살아 있어야** 나간다.
프로세스가 죽거나 기계가 꺼지면 아무 연락도 오지 않는다 — 가장 큰 장애일 때 가장 조용하다.

이건 앱 안에서 풀 수 없는 문제다. 대신 뒤집는다:
주기적으로 바깥에 "살아 있다" 를 보내고, **그게 끊기면** 바깥에서 알린다.
Healthchecks.io·Cronitor·BetterStack 같은 서비스가 이 규약을 쓴다.

핵심 규칙 하나: **준비되지 않았으면 보내지 않는다.**
DB 가 끊긴 채로 "살아 있다" 를 보내면 감시자는 정상이라고 믿는다.
그건 하트비트가 없는 것보다 나쁘다 — 없으면 최소한 의심이라도 한다.
"""

import asyncio
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0

# 마지막 상태. 운영자 화면에서 "하트비트가 돌고는 있나" 를 볼 수 있어야 한다.
_state: Dict[str, Any] = {
    "configured": False,
    "last_success": None,
    "last_failure": None,
    "last_error": None,
    "sent": 0,
}


def status() -> Dict[str, Any]:
    return dict(_state)


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # 하트비트가 실패했다고 서비스가 흔들리면 안 된다. 기록만 남긴다.
        _state["last_error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        return False


def beat_once() -> bool:
    """한 번 보낸다. 보냈으면 True.

    준비 상태를 먼저 확인한다. 안 되어 있으면 `/fail` 로 보내서 감시자가
    타임아웃을 기다리지 않고 바로 알리게 한다 (Healthchecks.io 규약).
    `/fail` 을 모르는 서비스면 그냥 무시되고, 그때는 신호가 끊긴 것으로 잡힌다.
    """
    url = settings.HEARTBEAT_URL
    if not url:
        return False

    from src.infrastructure.observability.health import readiness

    ready = False
    try:
        ready = bool(readiness()["ready"])
    except Exception:
        logger.warning("하트비트: 준비 상태 확인 실패", exc_info=True)

    target = url.rstrip("/") if ready else url.rstrip("/") + "/fail"
    ok = _ping(target)

    now = datetime.now(timezone.utc).isoformat()
    if ok and ready:
        _state["last_success"] = now
        _state["sent"] += 1
        _state["last_error"] = None
    else:
        _state["last_failure"] = now
        if not ready:
            _state["last_error"] = "준비되지 않아 실패 신호를 보냈습니다"
    return ok


async def run_forever() -> None:
    """앱이 사는 동안 계속 보낸다.

    별도 프로세스를 두지 않는다. 감시 장치가 앱보다 먼저 죽으면 아무 의미가 없고,
    운영해야 할 프로세스가 하나 늘면 그것 자체가 새로운 장애 지점이 된다.

    워커가 여럿이면 워커 수만큼 간다. 감시 서비스는 중복 신호를 무시하므로 문제가 없고,
    오히려 워커 하나가 죽어도 나머지가 보내서 "부분 장애" 를 놓친다는 한계가 생긴다.
    그건 준비 상태 점검(/health/ready)이 잡는 몫이다.
    """
    interval = max(30, settings.HEARTBEAT_INTERVAL_SECONDS)
    _state["configured"] = True
    logger.info("하트비트 시작 (%s초 간격)", interval)

    while True:
        try:
            # readiness 는 DB·Redis·저장소를 실제로 두드리는 동기 함수다.
            # 이벤트 루프에서 그대로 부르면 그 시간 동안 요청 처리가 멈춘다.
            await asyncio.to_thread(beat_once)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("하트비트 실패", exc_info=True)
        await asyncio.sleep(interval)


def start(loop_task_holder: list) -> Optional[asyncio.Task]:
    """설정돼 있을 때만 띄운다.

    테스트에서는 띄우지 않는다. 테스트가 바깥으로 요청을 보내면
    네트워크가 없는 환경에서 느려지고, 있는 환경에서는 남의 감시 서비스를 두드린다.
    """
    if not settings.HEARTBEAT_URL or settings.ENVIRONMENT == "test":
        return None
    task = asyncio.create_task(run_forever())
    loop_task_holder.append(task)
    return task
