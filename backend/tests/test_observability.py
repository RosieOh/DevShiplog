"""관측.

여기서 검증하려는 건 "로그가 예쁘게 나오는가" 가 아니라
**500 이 났을 때 그걸 알 방법이 있는가** 다.
"""

import json
import logging

import pytest
from fastapi import APIRouter

from src.domain.enums import UserRole
from src.infrastructure.database.models.user import User
from src.infrastructure.observability.context import request_id_var, user_id_var
from src.infrastructure.observability.errors import ErrorTracker
from src.infrastructure.observability.logging_setup import JsonFormatter
from src.main import app

# 일부러 터지는 경로. 라우터를 테스트에서만 붙였다 뗀다 —
# 실제 앱에 500 을 내는 경로를 남겨 두면 그게 곧 장애 버튼이다.
_boom = APIRouter()


@_boom.get("/__boom")
def boom():
    raise RuntimeError("일부러 터뜨린 오류")


@pytest.fixture()
def boom_client(db_session):
    """500 을 실제로 받아 보는 클라이언트.

    기본 TestClient 는 서버 예외를 그대로 다시 올려 보내서 응답을 볼 수 없다.
    우리가 확인하려는 건 "500 응답이 어떻게 생겼는가" 이므로 꺼야 한다.
    """
    from fastapi.testclient import TestClient

    from src.infrastructure.database.session import get_db

    app.include_router(_boom)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.router.routes = [
            route for route in app.router.routes if getattr(route, "path", "") != "/__boom"
        ]


# ------------------------------------------------------------------ 요청 ID


def test_response_carries_request_id(client):
    response = client.get("/health")
    assert response.headers.get("X-Request-ID")


def test_incoming_request_id_is_kept(client):
    """앞단이 붙인 ID 를 새로 만들면 프록시 로그와 앱 로그를 이을 수 없다."""
    response = client.get("/health", headers={"X-Request-ID": "from-proxy-123"})
    assert response.headers["X-Request-ID"] == "from-proxy-123"


def test_request_ids_differ_between_requests(client):
    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]
    assert first != second


# ------------------------------------------------------------------ 오류 수집


def test_unhandled_error_is_captured_and_traceable(boom_client):
    """500 응답에 추적 단서가 있어야 한다.

    사용자가 "오류가 났어요" 라고만 말하면 로그에서 그 요청을 찾을 방법이 없다.
    """
    from src.infrastructure.observability.errors import error_tracker

    error_tracker.reset()
    response = boom_client.get("/__boom")

    assert response.status_code == 500
    body = response.json()
    # 스택트레이스는 절대 나가면 안 된다.
    assert "RuntimeError" not in json.dumps(body)
    assert body["request_id"] and body["error_id"]

    captured = error_tracker.recent()
    assert len(captured) == 1
    assert captured[0]["type"] == "RuntimeError"
    assert captured[0]["path"] == "/__boom"
    assert captured[0]["fingerprint"] == body["error_id"]


def test_same_error_is_grouped_not_repeated():
    """같은 오류 1000건이 화면을 채우면 무엇부터 고칠지 알 수 없다."""
    tracker = ErrorTracker()

    def raise_it(n):
        raise ValueError(f"주문 {n} 실패")  # 메시지가 매번 다르다

    for i in range(5):
        try:
            raise_it(i)
        except ValueError as exc:
            tracker.capture(exc, path="/orders")

    groups = tracker.recent()
    assert len(groups) == 1
    assert groups[0]["count"] == 5
    assert tracker.total() == 5


def test_different_places_are_separate_groups():
    tracker = ErrorTracker()
    try:
        raise ValueError("A")
    except ValueError as exc:
        tracker.capture(exc, path="/a")
    try:
        raise ValueError("B")
    except ValueError as exc:
        tracker.capture(exc, path="/b")
    assert len(tracker.recent()) == 2


def test_group_cap_keeps_the_newest():
    """무한히 쌓이면 메모리가 샌다. 오래 안 보인 것부터 버린다."""
    tracker = ErrorTracker()
    for i in range(80):
        try:
            raise ValueError("x")
        except ValueError as exc:
            tracker.capture(exc, path=f"/path-{i}")
    groups = tracker.recent(limit=100)
    assert len(groups) <= 50
    assert groups[0]["path"] == "/path-79"


# ------------------------------------------------------------------ 구조화 로그


def test_json_log_includes_request_context():
    formatter = JsonFormatter()
    token = request_id_var.set("req-abc")
    user_token = user_id_var.set("user-9")
    try:
        record = logging.LogRecord(
            "access", logging.INFO, __file__, 1, "GET /posts 200", (), None
        )
        record.duration_ms = 12.5
        record.status = 200
        payload = json.loads(formatter.format(record))
    finally:
        request_id_var.reset(token)
        user_id_var.reset(user_token)

    assert payload["request_id"] == "req-abc"
    assert payload["user_id"] == "user-9"
    assert payload["duration_ms"] == 12.5
    assert payload["status"] == 200
    assert payload["msg"] == "GET /posts 200"


def test_json_log_without_context_omits_fields():
    payload = json.loads(
        JsonFormatter().format(
            logging.LogRecord("x", logging.INFO, __file__, 1, "hi", (), None)
        )
    )
    assert "request_id" not in payload


# ------------------------------------------------------------------ 준비 상태


def test_readiness_reports_each_dependency(client):
    """`{"status":"healthy"}` 만으로는 DB 가 끊겨도 healthy 라고 답한다.

    실제로 붙는지(ok)는 여기서 단정하지 않는다.
    준비 상태 점검은 테스트용 인메모리 SQLite 가 아니라 **앱이 진짜로 쓸 DB** 를 두드린다.
    그게 맞는 동작이다 — 테스트 세션을 보고 "준비됐다" 고 답하면 점검이 아니다.
    대신 그래서 이 값은 환경에 따라 달라지므로, 여기서는 구조와 필수 여부만 본다.
    붙었을 때/끊겼을 때의 응답은 아래 두 테스트가 각각 확인한다.
    """
    body = client.get("/health/ready").json()
    checks = {check["name"]: check for check in body["checks"]}
    assert set(checks) == {"database", "redis", "storage"}
    assert checks["database"]["required"] is True

    # Redis 가 끊겨도 글 읽기·쓰기는 된다. 필수로 두면 Redis 재시작에
    # 서비스 전체가 트래픽에서 빠진다 — 실제로는 조금 불편해질 뿐인데.
    assert checks["redis"]["required"] is False

    # 응답 코드는 판정을 따라가야 한다. 둘이 어긋나면 로드밸런서가 엉뚱하게 움직인다.
    assert client.get("/health/ready").status_code == (200 if body["ready"] else 503)


def test_readiness_returns_200_when_required_dependencies_are_up(client, monkeypatch):
    """필수 의존성이 살아 있으면 트래픽을 받아야 한다."""
    import src.infrastructure.observability.health as health

    monkeypatch.setattr(health, "_check_database", lambda: None)
    monkeypatch.setattr(health, "_check_storage", lambda: None)
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_readiness_returns_503_when_required_dependency_is_down(client, monkeypatch):
    """준비되지 않았는데 200 을 내면 로드밸런서가 죽은 인스턴스로 계속 보낸다."""
    import src.infrastructure.observability.health as health

    def broken():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(health, "_check_database", broken)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["ready"] is False


def test_admin_can_see_errors_and_readiness(
    client, db_session, auth_headers, boom_client, monkeypatch
):
    from src.infrastructure.observability.errors import error_tracker

    error_tracker.reset()
    # 화면은 이제 DB 를 읽는다. 테스트 세션을 쓰도록 붙여 준다.
    monkeypatch.setattr("src.infrastructure.observability.errors.session_factory",
                        lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    boom_client.get("/__boom")

    user_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]
    user = db_session.query(User).filter(User.id == user_id).first()
    user.role = UserRole.ADMIN
    db_session.commit()

    errors = client.get("/api/v1/admin/errors", headers=auth_headers).json()
    assert errors["items"][0]["type"] == "RuntimeError"
    assert errors["error_groups"] == 1
    # 알림 통로가 설정돼 있는지 화면이 알아야 한다.
    # 안 그러면 "오류가 나면 연락이 오겠지" 라고 믿은 채로 아무 연락도 안 온다.
    assert errors["alerting"] is False

    assert client.get("/api/v1/admin/readiness", headers=auth_headers).json()["checks"]
