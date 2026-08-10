"""오류 수집.

"서버에서 500 이 나도 아무도 모른다" 를 없애는 게 목적이다.

기록은 두 곳에 남는다.
- 메모리: 이 워커에서 방금 난 것. 잠그지 않고 빠르게 센다.
- DB(error_groups): 재시작해도, 워커가 여럿이어도 남는다. 화면은 이쪽을 본다.

처음에는 메모리에만 두었다. 그랬더니 재시작하면 사라지고 워커가 여럿이면 일부만 보여서
"어제 밤에 뭐가 터졌지" 를 물을 수 없었다. 그건 기록이 아니다.

저장이 실패해도 요청은 그대로 진행된다. DB 가 끊긴 것이 원인인 오류를 DB 에 적으려다
또 터지면 원래 오류가 묻힌다.

처음 보는 지문이면 알림도 보낸다 (alerts). 화면에 쌓여도 아무도 안 보면 모르는 것과 같다.
SENTRY_DSN 이 있으면 그쪽으로도 보내되, 없어도 그대로 돈다.
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

        # DB 에도 남긴다. 메모리만으로는 재시작하면 사라지고 워커가 여럿이면
        # 일부만 보인다. 실패해도 메모리 기록은 이미 끝났으므로 삼킨다 —
        # DB 가 끊긴 것이 원인인 오류를 DB 에 적으려다 또 터지면 원래 오류가 묻힌다.
        is_new = _persist(group, request_id)

        # 알림은 처음 보는 오류에만. 이미 아는 오류가 계속 나는 것은
        # 알림이 아니라 화면에서 볼 일이다.
        if is_new:
            _notify_new(group, request_id)

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


# 테스트가 갈아끼운다. None 이면 앱이 실제로 쓰는 DB 를 늦게 가져온다.
#
# 이 갈고리가 없으면 테스트 스위트가 개발자의 진짜 데이터베이스에 기록한다.
# 실제로 그랬다 — 일부러 터뜨린 오류 84그룹이 개발 DB 에 쌓여 있었다.
# 테스트는 자기가 만든 것 말고는 아무것도 건드리지 않아야 한다.
session_factory = None


def _persist(group: Dict[str, Any], request_id: Optional[str]) -> bool:
    """지문별로 하나의 행을 유지한다. 처음 만들어졌으면 True.

    자체 세션을 연다 — 여기는 요청 세션이 이미 롤백된 뒤일 수 있다.
    UPDATE 를 먼저 시도하고 없을 때만 INSERT 한다. 워커가 여럿이면 같은 지문을
    동시에 만들려 할 수 있어서, 유니크 충돌은 "누가 먼저 만들었다" 로 읽고 UPDATE 로 돌아간다.
    """
    try:
        from sqlalchemy.exc import IntegrityError

        from src.infrastructure.config.settings import settings
        from src.infrastructure.database.models.error_group import ErrorGroup

        factory = session_factory
        if factory is None:
            if settings.ENVIRONMENT == "test":
                # 테스트에서 세션을 지정하지 않았으면 아무 데도 쓰지 않는다.
                return False
            from src.infrastructure.database.session import SessionLocal

            factory = SessionLocal
    except Exception:
        return False

    # DB 는 시간대 없는 UTC 로 다룬다 (다른 표와 같은 규칙).
    now = group["last_seen"].replace(tzinfo=None)
    db = None
    try:
        db = factory()
        updated = (
            db.query(ErrorGroup)
            .filter(ErrorGroup.fingerprint == group["fingerprint"])
            .update(
                {
                    ErrorGroup.count: ErrorGroup.count + 1,
                    ErrorGroup.last_seen: now,
                    ErrorGroup.last_request_id: request_id,
                    ErrorGroup.message: group["message"],
                    # 다시 났으면 확인 처리를 풀어야 한다. 안 그러면 재발이 묻힌다.
                    ErrorGroup.resolved_at: None,
                },
                synchronize_session=False,
            )
        )
        if updated:
            db.commit()
            return False

        db.add(
            ErrorGroup(
                fingerprint=group["fingerprint"],
                type=group["type"],
                message=group["message"],
                origin=group["origin"][:500] if group["origin"] else None,
                path=group["path"],
                method=group["method"],
                traceback=group["traceback"],
                count=1,
                first_seen=now,
                last_seen=now,
                last_request_id=request_id,
            )
        )
        try:
            db.commit()
            return True
        except IntegrityError:
            # 다른 워커가 한 발 빨랐다. 그쪽이 "처음" 이므로 우리는 세기만 한다.
            db.rollback()
            db.query(ErrorGroup).filter(
                ErrorGroup.fingerprint == group["fingerprint"]
            ).update({ErrorGroup.count: ErrorGroup.count + 1}, synchronize_session=False)
            db.commit()
            return False
    except Exception:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        logger.warning("오류 기록 저장 실패 — 메모리에만 남습니다", exc_info=True)
        return False
    finally:
        if db is not None:
            db.close()


def stored_recent(db, limit: int = 20, include_resolved: bool = False) -> List[Dict[str, Any]]:
    """DB 에 남은 오류. 화면은 이쪽을 본다.

    메모리 수집기는 이제 "지금 이 워커에서 방금 난 것" 을 아는 용도로만 남는다.
    """
    from src.infrastructure.database.models.error_group import ErrorGroup

    query = db.query(ErrorGroup)
    if not include_resolved:
        query = query.filter(ErrorGroup.resolved_at.is_(None))
    rows = query.order_by(ErrorGroup.last_seen.desc()).limit(limit).all()
    return [
        {
            "fingerprint": row.fingerprint,
            "type": row.type,
            "message": row.message or "",
            "origin": row.origin or "",
            "path": row.path,
            "method": row.method,
            "count": row.count,
            "first_seen": _as_utc(row.first_seen),
            "last_seen": _as_utc(row.last_seen),
            "last_request_id": row.last_request_id,
            "resolved_at": _as_utc(row.resolved_at),
            "traceback": row.traceback or "",
        }
        for row in rows
    ]


def stored_summary(db) -> Dict[str, int]:
    from sqlalchemy import func as sa_func

    from src.infrastructure.database.models.error_group import ErrorGroup

    groups, events = (
        db.query(sa_func.count(ErrorGroup.id), sa_func.coalesce(sa_func.sum(ErrorGroup.count), 0))
        .filter(ErrorGroup.resolved_at.is_(None))
        .one()
    )
    return {"error_groups": int(groups or 0), "error_events": int(events or 0)}


def mark_resolved(db, fingerprint: str) -> bool:
    """운영자가 확인 처리. 행은 지우지 않는다 — 다시 나면 count 가 올라가야 하고,
    "전에도 있었다" 를 아는 것이 재발 판단의 전부다."""
    from src.infrastructure.database.models.error_group import ErrorGroup

    updated = (
        db.query(ErrorGroup)
        .filter(ErrorGroup.fingerprint == fingerprint, ErrorGroup.resolved_at.is_(None))
        .update(
            {ErrorGroup.resolved_at: datetime.now(timezone.utc).replace(tzinfo=None)},
            synchronize_session=False,
        )
    )
    db.commit()
    return bool(updated)


def _as_utc(value) -> Optional[str]:
    """DB 의 시간대 없는 UTC 를 UTC 표시가 붙은 ISO 로.

    표시를 빼면 브라우저가 현지 시각으로 읽어서 방금 난 오류가 몇 시간 전으로 보인다.
    """
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _notify_new(group: Dict[str, Any], request_id: Optional[str]) -> None:
    try:
        from src.infrastructure.observability import alerts

        alerts.new_error(
            fingerprint=group["fingerprint"],
            type_name=group["type"],
            message=group["message"],
            path=group["path"],
            origin=group["origin"],
            request_id=request_id,
        )
    except Exception:
        # 알리다 터진 것으로 원래 오류를 덮지 않는다.
        logger.warning("오류 알림 실패", exc_info=True)


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
