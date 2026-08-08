"""오류 수집.

"서버에서 500 이 나도 아무도 모른다" 를 없애는 게 목적이다.

Sentry 를 붙일 수 있게 해 두되, 없어도 동작해야 한다.
1인 개발 단계에서 외부 서비스 가입을 전제로 하면 결국 아무것도 안 붙이고 넘어가게 된다.
그래서 프로세스 안에 최근 오류를 모아 두고 운영자 화면에서 바로 본다.

한계는 분명하다 — 메모리에만 있으므로 재시작하면 사라지고, 워커가 여러 개면
요청이 닿은 워커의 것만 보인다. 그래서 SENTRY_DSN 이 있으면 그쪽으로도 보낸다.
이 한계는 화면에도 적어 둔다. 모르고 믿는 게 없는 것보다 나쁘다.
"""

import hashlib
import logging
import threading
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MAX_GROUPS = 50


class ErrorTracker:
    """최근 오류를 지문별로 묶어 둔다.

    한 건씩 쌓으면 같은 오류가 1000번 나는 순간 화면이 그것만으로 가득 찬다.
    묶어야 "무엇이 몇 번" 이 보이고, 그래야 무엇부터 고칠지 정할 수 있다.
    """

    def __init__(self) -> None:
        # 배경 작업(Celery)과 요청이 같이 쓴다. 딕셔너리 갱신이 겹치면 수가 어긋난다.
        self._lock = threading.Lock()
        self._groups: Dict[str, Dict[str, Any]] = {}
        # 시각으로 정렬하지 않는다. 같은 밀리초에 여러 건이 들어오면 순서가 뒤집히고,
        # 그러면 "가장 오래 안 보인 것부터 버린다" 는 규칙이 사실상 무작위가 된다.
        self._seq = 0

    def capture(
        self,
        exc: BaseException,
        *,
        path: Optional[str] = None,
        method: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        frames = traceback.extract_tb(exc.__traceback__)
        # 지문은 "예외 타입 + 마지막 우리 코드 위치" 로 만든다.
        # 메시지를 넣으면 ID 가 섞인 메시지 때문에 같은 버그가 매번 새 그룹이 된다.
        origin = ""
        for frame in reversed(frames):
            if "site-packages" not in frame.filename:
                origin = f"{frame.filename}:{frame.lineno}"
                break
        fingerprint = hashlib.sha1(
            f"{type(exc).__name__}|{origin}|{path or ''}".encode()
        ).hexdigest()[:12]

        now = datetime.now(timezone.utc)
        with self._lock:
            group = self._groups.get(fingerprint)
            if group is None:
                if len(self._groups) >= _MAX_GROUPS:
                    # 가장 오래 안 보인 그룹을 버린다. 지금 나는 오류가 더 중요하다.
                    oldest = min(self._groups, key=lambda k: self._groups[k]["seq"])
                    del self._groups[oldest]
                group = {
                    "fingerprint": fingerprint,
                    "type": type(exc).__name__,
                    "message": str(exc)[:300],
                    "origin": origin,
                    "path": path,
                    "method": method,
                    "count": 0,
                    "seq": 0,
                    "first_seen": now,
                    "traceback": "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )[-4000:],
                }
                self._groups[fingerprint] = group
            group["count"] += 1
            group["last_seen"] = now
            self._seq += 1
            group["seq"] = self._seq
            group["last_request_id"] = request_id

        _send_to_sentry(exc)
        return fingerprint

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            groups = sorted(self._groups.values(), key=lambda g: g["seq"], reverse=True)
            return [
                {
                    **{k: v for k, v in group.items() if k not in ("traceback", "seq")},
                    "first_seen": group["first_seen"].isoformat(),
                    "last_seen": group["last_seen"].isoformat(),
                    "traceback": group["traceback"],
                }
                for group in groups[:limit]
            ]

    def total(self) -> int:
        with self._lock:
            return sum(group["count"] for group in self._groups.values())

    def reset(self) -> None:
        with self._lock:
            self._groups.clear()


error_tracker = ErrorTracker()

_sentry_ready = False


def init_error_tracking(dsn: str, environment: str, release: str) -> bool:
    """Sentry 가 설치·설정돼 있으면 켠다.

    없으면 조용히 넘어간다. 관측 설정이 기동을 막으면 안 된다 —
    관측은 서비스를 돕는 것이지 서비스의 전제 조건이 아니다.
    """
    global _sentry_ready
    if not dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            # 성능 추적은 기본으로 끈다. 켜면 비용이 붙고, 지금 필요한 건 오류다.
            traces_sample_rate=0.0,
            send_default_pii=False,
        )
        _sentry_ready = True
        logger.info("에러 추적 활성화", extra={"backend": "sentry"})
    except ImportError:
        logger.warning("SENTRY_DSN 이 있지만 sentry-sdk 가 설치돼 있지 않습니다")
    except Exception:
        logger.warning("에러 추적 초기화 실패", exc_info=True)
    return _sentry_ready


def _send_to_sentry(exc: BaseException) -> None:
    if not _sentry_ready:
        return
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception:
        # 오류를 보고하다 오류가 나면 원래 오류가 묻힌다. 절대 밖으로 내보내지 않는다.
        logger.debug("Sentry 전송 실패", exc_info=True)
