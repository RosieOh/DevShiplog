"""알림.

오류가 화면에 쌓여도 아무도 안 보면 모르는 것과 같다.
알림이 없으면 관측은 "사후에 확인할 수 있다" 까지고, 그건 장애 중에는 쓸모가 없다.

두 가지만 보낸다.
- 처음 보는 오류
- 새 신고

둘 다 **묶고 조인다.** 알림이 쏟아지면 사람은 알림을 끈다.
끈 알림은 없는 알림이고, 없느니만 못하다 — 있다고 믿게 되니까.
"""

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Optional

from src.infrastructure.config.settings import settings
from src.infrastructure.external import mail

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0


class _Throttle:
    """키별로 "이 시간 안에 한 번만" 을 강제한다.

    프로세스 안에만 있다. 워커가 여럿이면 워커 수만큼 갈 수 있다 —
    완벽한 중복 제거가 아니라 폭주 방지가 목적이다. 오류마다 하나씩 오는 것과
    같은 오류로 1000통이 오는 것의 차이가 크지, 1통과 3통의 차이는 크지 않다.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}

    def allow(self, key: str, window_seconds: float) -> bool:
        now = time.monotonic()
        with self._lock:
            previous = self._last.get(key)
            if previous is not None and now - previous < window_seconds:
                return False
            self._last[key] = now
            # 키가 무한히 늘지 않게 창을 한참 지난 것은 버린다.
            if len(self._last) > 500:
                cutoff = now - max(window_seconds, 3600) * 2
                self._last = {k: v for k, v in self._last.items() if v > cutoff}
            return True

    def reset(self) -> None:
        with self._lock:
            self._last.clear()


_throttle = _Throttle()


def _post_webhook(text: str) -> bool:
    """Slack·Discord 호환 형태로 보낸다.

    두 서비스 모두 {"text": ...} / {"content": ...} 를 받으므로 둘 다 넣는다.
    받는 쪽이 모르는 키는 무시한다.
    """
    if not settings.ALERT_WEBHOOK_URL:
        return False
    payload = json.dumps({"text": text, "content": text}).encode("utf-8")
    request = urllib.request.Request(
        settings.ALERT_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        # 알림을 보내다 난 오류를 다시 알림으로 보내면 무한이 된다. 로그까지만.
        logger.warning("웹훅 알림 실패", exc_info=True)
        return False


def _send(subject: str, body: str) -> bool:
    """설정된 통로로 모두 보낸다. 하나라도 나가면 성공으로 본다."""
    delivered = False
    if settings.ALERT_EMAIL:
        delivered = mail.send(settings.ALERT_EMAIL, subject, body) or delivered
    if settings.ALERT_WEBHOOK_URL:
        delivered = _post_webhook(f"{subject}\n\n{body}") or delivered
    if not delivered:
        # 통로가 없으면 조용히 넘어가지 않는다. 설정을 안 한 것도 알아야 한다.
        logger.info("[알림 미발송 — 통로 미설정] %s", subject)
    return delivered


def _site(path: str) -> str:
    base = (settings.FRONTEND_ORIGIN or "").rstrip("/")
    return f"{base}{path}" if base else path


def new_error(*, fingerprint: str, type_name: str, message: str, path: Optional[str],
              origin: str, request_id: Optional[str]) -> bool:
    """처음 보는 오류.

    같은 지문은 창 안에 한 번만. 이미 아는 오류가 계속 나는 것은
    알림이 아니라 화면에서 볼 일이다.
    """
    if not _throttle.allow(f"error:{fingerprint}", settings.ALERT_ERROR_WINDOW_MINUTES * 60):
        return False
    body = "\n".join(
        [
            f"{type_name}: {message}",
            f"경로: {path or '-'}",
            f"위치: {origin or '-'}",
            f"요청 ID: {request_id or '-'}",
            "",
            _site("/admin"),
        ]
    )
    return _send(f"[Devshiplog] 새 오류 — {type_name}", body)


def new_report(*, reason: str, target_type: str, pending: int) -> bool:
    """새 신고.

    신고 하나하나가 아니라 "밀린 게 있다" 를 알린다.
    신고가 몰릴 때 한 건마다 보내면 그때가 바로 알림을 끄는 순간이다.
    """
    if not _throttle.allow("report", settings.ALERT_REPORT_WINDOW_MINUTES * 60):
        return False
    body = "\n".join(
        [
            f"새 신고: {target_type} · 사유 {reason}",
            f"처리 대기 {pending}건",
            "",
            _site("/admin/reports"),
        ]
    )
    return _send(f"[Devshiplog] 신고 {pending}건 대기", body)


def reset() -> None:
    """테스트용."""
    _throttle.reset()
