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
    """`{"status":"healthy"}` 만으로는 DB 가 끊겨도 healthy 라고 답한다."""
    response = client.get("/health/ready")
    body = response.json()
    names = {check["name"] for check in body["checks"]}
    assert names == {"database", "redis", "storage"}

    database = next(c for c in body["checks"] if c["name"] == "database")
    assert database["ok"] is True and database["required"] is True

    # Redis 가 없는 환경에서도 DB 만 살아 있으면 준비된 것으로 본다.
    # Redis 를 required 로 두면 Redis 재시작에 서비스 전체가 트래픽에서 빠진다.
    redis_check = next(c for c in body["checks"] if c["name"] == "redis")
    assert redis_check["required"] is False
    assert response.status_code == 200


def test_readiness_returns_503_when_required_dependency_is_down(client, monkeypatch):
    """준비되지 않았는데 200 을 내면 로드밸런서가 죽은 인스턴스로 계속 보낸다."""
    import src.infrastructure.observability.health as health

    def broken():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(health, "_check_database", broken)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["ready"] is False


def test_admin_can_see_errors_and_readiness(client, db_session, auth_headers, boom_client):
    from src.infrastructure.observability.errors import error_tracker

    error_tracker.reset()
    boom_client.get("/__boom")

    user_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]
    user = db_session.query(User).filter(User.id == user_id).first()
    user.role = UserRole.ADMIN
    db_session.commit()

    errors = client.get("/api/v1/admin/errors", headers=auth_headers).json()
    assert errors["items"][0]["type"] == "RuntimeError"
    # 한계를 화면에도 적어 둔다. 모르고 믿는 게 없는 것보다 나쁘다.
    assert "재시작" in errors["note"]

    assert client.get("/api/v1/admin/readiness", headers=auth_headers).json()["checks"]
