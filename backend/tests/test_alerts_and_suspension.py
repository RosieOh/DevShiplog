"""알림 · 오류 영속화 · 사용자 정지.

이 세 가지가 없으면 다음이 성립한다.
- 오류가 나도 아무도 모른다 (알림 없음)
- 재시작하면 무슨 일이 있었는지 알 수 없다 (메모리에만 기록)
- 같은 사람이 반복해도 글을 하나씩 내리는 것 외에 할 게 없다 (정지 없음)
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import APIRouter

from src.domain.enums import DraftStatus, UserRole
from src.infrastructure.database.models.draft import Draft
from src.infrastructure.database.models.error_group import ErrorGroup
from src.infrastructure.database.models.user import User
from src.infrastructure.observability import alerts
from src.main import app

TITLE = "정지 테스트 글"
BODY = "정지와 알림을 확인하기 위한 본문입니다. 최소 길이를 넘기려고 충분히 길게 적습니다."


# ------------------------------------------------------------------ 픽스처


@pytest.fixture(autouse=True)
def _quiet_alerts(monkeypatch):
    """알림은 기본적으로 삼킨다. 확인할 때만 sent 리스트를 본다."""
    alerts.reset()
    sent = []
    monkeypatch.setattr(alerts, "_send", lambda subject, body: sent.append((subject, body)) or True)
    yield sent
    alerts.reset()


def _uid(client, headers) -> str:
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def _promote(db_session, client, headers):
    user = db_session.query(User).filter(User.id == _uid(client, headers)).first()
    user.role = UserRole.ADMIN
    db_session.commit()


def _publish(client, db_session, headers, title=TITLE):
    draft = Draft(
        id=str(uuid.uuid4()),
        user_id=_uid(client, headers),
        type="implementation",
        audience="intermediate",
        length_preset="default",
        status=DraftStatus.ACTIVE,
    )
    db_session.add(draft)
    db_session.commit()
    client.put(f"/api/v1/drafts/{draft.id}/content", headers=headers, json={"content_md": BODY})
    response = client.post(
        "/api/v1/posts", headers=headers, json={"draft_id": draft.id, "title": title, "tags": []}
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def bloggers(client, auth_headers, other_auth_headers):
    client.put("/api/v1/profile/me", headers=auth_headers, json={"handle": "author"})
    client.put("/api/v1/profile/me", headers=other_auth_headers, json={"handle": "reader"})


# --------------------------------------------------------------- 알림 조이기


def test_alert_is_throttled_per_fingerprint(_quiet_alerts):
    """같은 오류로 알림이 쏟아지면 사람은 알림을 끈다. 끈 알림은 없느니만 못하다."""
    for _ in range(5):
        alerts.new_error(
            fingerprint="abc123",
            type_name="RuntimeError",
            message="같은 오류",
            path="/x",
            origin="a.py:1",
            request_id="r1",
        )
    assert len(_quiet_alerts) == 1


def test_different_errors_alert_separately(_quiet_alerts):
    for fingerprint in ("aaa", "bbb"):
        alerts.new_error(
            fingerprint=fingerprint,
            type_name="ValueError",
            message="다름",
            path="/y",
            origin="b.py:2",
            request_id=None,
        )
    assert len(_quiet_alerts) == 2


def test_report_alerts_are_batched(_quiet_alerts):
    """신고가 몰릴 때 한 건마다 보내면 그때가 바로 알림을 끄는 순간이다."""
    for _ in range(4):
        alerts.new_report(reason="spam", target_type="post", pending=3)
    assert len(_quiet_alerts) == 1
    assert "3건" in _quiet_alerts[0][0]


def test_alert_body_points_at_the_screen(_quiet_alerts):
    """어디로 가야 하는지 없으면 알림을 받고도 찾아 헤맨다."""
    alerts.new_error(
        fingerprint="zzz",
        type_name="KeyError",
        message="없음",
        path="/posts",
        origin="c.py:3",
        request_id="req-9",
    )
    _, body = _quiet_alerts[0]
    assert "/admin" in body and "req-9" in body


# ------------------------------------------------------ 오류가 DB 에 남는가

_boom = APIRouter()


@_boom.get("/__boom2")
def boom():
    raise RuntimeError("영속화 확인용 오류")


@pytest.fixture()
def boom_client(db_session):
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
            r for r in app.router.routes if getattr(r, "path", "") != "/__boom2"
        ]


def test_error_survives_in_the_database(boom_client, db_session, monkeypatch):
    """메모리에만 있으면 재시작하는 순간 "어제 뭐가 터졌지" 를 물을 수 없다."""
    monkeypatch.setattr("src.infrastructure.observability.errors.session_factory",
                        lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    boom_client.get("/__boom2")
    boom_client.get("/__boom2")

    rows = db_session.query(ErrorGroup).all()
    # 한 건씩 쌓지 않고 묶는다. 같은 오류 1000건이 표를 채우면 무엇부터 고칠지 모른다.
    assert len(rows) == 1
    assert rows[0].count == 2
    assert rows[0].type == "RuntimeError"


def test_admin_sees_persisted_errors_and_can_resolve(
    client, boom_client, db_session, auth_headers, monkeypatch
):
    monkeypatch.setattr("src.infrastructure.observability.errors.session_factory",
                        lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    boom_client.get("/__boom2")
    _promote(db_session, client, auth_headers)

    listed = client.get("/api/v1/admin/errors", headers=auth_headers).json()
    assert listed["error_groups"] == 1
    fingerprint = listed["items"][0]["fingerprint"]

    assert client.post(
        f"/api/v1/admin/errors/{fingerprint}/resolve", headers=auth_headers
    ).status_code == 200
    assert client.get("/api/v1/admin/errors", headers=auth_headers).json()["items"] == []

    # 지우지 않는다. 다시 나면 목록에 돌아와야 재발을 안다.
    assert db_session.query(ErrorGroup).count() == 1


def test_resolving_unknown_error_is_404(client, db_session, auth_headers):
    _promote(db_session, client, auth_headers)
    assert client.post(
        "/api/v1/admin/errors/nope/resolve", headers=auth_headers
    ).status_code == 404


# ------------------------------------------------------------------ 정지


def test_suspended_user_cannot_write_but_can_read(
    client, db_session, auth_headers, other_auth_headers, bloggers
):
    """읽기까지 막으면 무슨 일이 일어났는지 알 방법이 없다. 그건 처벌이 아니라 방치다."""
    _promote(db_session, client, auth_headers)
    client.post(
        "/api/v1/admin/users/reader/suspend",
        headers=auth_headers,
        json={"days": 3, "reason": "스팸 반복"},
    )

    blocked = client.post(
        "/api/v1/social/users/author/follow", headers=other_auth_headers
    )
    assert blocked.status_code == 403
    detail = blocked.json()["detail"]
    # 사유를 안 알려주면 항의만 부르고 행동은 바뀌지 않는다.
    assert detail["reason"] == "스팸 반복"
    assert detail["suspended_until"]

    assert client.get("/api/v1/profile/me", headers=other_auth_headers).status_code == 200


def test_suspension_expires_on_its_own(
    client, db_session, auth_headers, other_auth_headers, bloggers
):
    """운영자가 해제를 잊어도 사용자가 무기한 갇히지 않아야 한다."""
    _promote(db_session, client, auth_headers)
    reader = db_session.query(User).filter(User.handle == "reader").first()
    reader.suspended_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    db_session.commit()

    assert client.post(
        "/api/v1/social/users/author/follow", headers=other_auth_headers
    ).status_code == 200


def test_unsuspend_restores_writing(
    client, db_session, auth_headers, other_auth_headers, bloggers
):
    """오판이었다면 바로 되돌릴 수 있어야 한다."""
    _promote(db_session, client, auth_headers)
    client.post(
        "/api/v1/admin/users/reader/suspend", headers=auth_headers, json={"days": 7}
    )
    assert client.post(
        "/api/v1/social/users/author/follow", headers=other_auth_headers
    ).status_code == 403

    client.post("/api/v1/admin/users/reader/unsuspend", headers=auth_headers)
    assert client.post(
        "/api/v1/social/users/author/follow", headers=other_auth_headers
    ).status_code == 200


def test_admin_cannot_suspend_self_or_other_admins(
    client, db_session, auth_headers, other_auth_headers, bloggers
):
    """자기 발등을 찍으면 풀어 줄 사람이 없다."""
    _promote(db_session, client, auth_headers)
    assert client.post(
        "/api/v1/admin/users/author/suspend", headers=auth_headers, json={"days": 1}
    ).status_code == 422

    _promote(db_session, client, other_auth_headers)
    assert client.post(
        "/api/v1/admin/users/reader/suspend", headers=auth_headers, json={"days": 1}
    ).status_code == 422


def test_permanent_suspension_is_not_possible(client, db_session, auth_headers, bloggers):
    """되돌릴 수 없는 조치는 오판했을 때 고칠 방법이 없다."""
    _promote(db_session, client, auth_headers)
    for days in (0, 366, -1):
        assert client.post(
            "/api/v1/admin/users/reader/suspend", headers=auth_headers, json={"days": days}
        ).status_code == 422


def test_suspended_list_shows_only_active_ones(
    client, db_session, auth_headers, other_auth_headers, bloggers
):
    """걸어 놓고 잊는 것을 막는다. 기한이 지난 것은 저절로 풀리므로 보여주지 않는다."""
    _promote(db_session, client, auth_headers)
    client.post(
        "/api/v1/admin/users/reader/suspend", headers=auth_headers, json={"days": 5}
    )
    items = client.get("/api/v1/admin/users/suspended", headers=auth_headers).json()["items"]
    assert [i["handle"] for i in items] == ["reader"]

    reader = db_session.query(User).filter(User.handle == "reader").first()
    reader.suspended_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    db_session.commit()
    assert client.get("/api/v1/admin/users/suspended", headers=auth_headers).json()["items"] == []


def test_resolving_report_can_suspend_the_author(
    client, db_session, auth_headers, other_auth_headers, bloggers
):
    """신고를 처리하고 다시 사용자를 찾아 들어가야 하면 그 단계에서 그만두게 된다."""
    post = _publish(client, db_session, other_auth_headers)
    client.post(
        "/api/v1/social/reports",
        headers=auth_headers,
        json={"target_type": "post", "target_id": post["id"], "reason": "spam"},
    )
    _promote(db_session, client, auth_headers)
    report_id = client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"][0]["id"]

    result = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=auth_headers,
        json={"status": "resolved", "unpublish_post": True, "suspend_author_days": 7},
    ).json()

    assert result["unpublished"] is True
    assert result["suspended_until"]
    assert client.post(
        "/api/v1/social/users/author/follow", headers=other_auth_headers
    ).status_code == 403


def test_report_notifies_the_admin(client, db_session, auth_headers, other_auth_headers,
                                   bloggers, _quiet_alerts):
    """신고 화면을 만들어도 들여다볼 이유가 없으면 아무도 안 본다."""
    post = _publish(client, db_session, other_auth_headers)
    client.post(
        "/api/v1/social/reports",
        headers=auth_headers,
        json={"target_type": "post", "target_id": post["id"], "reason": "abuse"},
    )
    assert any("신고" in subject for subject, _ in _quiet_alerts)
