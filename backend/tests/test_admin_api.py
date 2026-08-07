"""운영자 권한과 신고 처리.

신고는 쌓이는데 볼 화면이 없으면 신고 기능은 장식이다.
여기서 검증하는 건 두 가지다 — 아무나 못 본다, 그리고 운영자는 실제로 처리할 수 있다.
"""

import uuid
from datetime import datetime, timezone

import pytest

from src.domain.enums import DraftStatus, UserRole
from src.infrastructure.database.models.draft import Draft
from src.infrastructure.database.models.user import User

TITLE = "신고 대상 글"
BODY = "이 글은 운영자 테스트를 위한 본문입니다. 최소 길이를 넘기기 위해 충분히 길게 씁니다."


def _uid(client, headers) -> str:
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def _publish(client, db_session, headers, title=TITLE):
    user_id = _uid(client, headers)
    draft = Draft(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type="implementation",
        audience="intermediate",
        length_preset="default",
        status=DraftStatus.ACTIVE,
    )
    db_session.add(draft)
    db_session.commit()
    client.put(f"/api/v1/drafts/{draft.id}/content", headers=headers, json={"content_md": BODY})
    r = client.post(
        "/api/v1/posts", headers=headers, json={"draft_id": draft.id, "title": title, "tags": []}
    )
    assert r.status_code == 201, r.text
    return r.json()


def _promote(db_session, client, headers):
    user = db_session.query(User).filter(User.id == _uid(client, headers)).first()
    user.role = UserRole.ADMIN
    db_session.commit()


@pytest.fixture()
def reported(client, db_session, auth_headers, other_auth_headers):
    """작성자가 글을 쓰고, 다른 사람이 신고한 상태."""
    client.put("/api/v1/profile/me", headers=auth_headers, json={"handle": "author"})
    client.put("/api/v1/profile/me", headers=other_auth_headers, json={"handle": "reader"})
    post = _publish(client, db_session, auth_headers)
    r = client.post(
        "/api/v1/social/reports",
        headers=other_auth_headers,
        json={"target_type": "post", "target_id": post["id"], "reason": "spam"},
    )
    assert r.status_code == 201, r.text
    return post


# ------------------------------------------------------------------ 권한


def test_normal_user_cannot_see_reports(client, reported, other_auth_headers):
    """일반 사용자에게는 404 다.

    403 이면 "그런 화면이 있긴 하다" 를 알려주는 셈이라 굳이 광고하지 않는다.
    """
    assert client.get("/api/v1/admin/reports", headers=other_auth_headers).status_code == 404


def test_anonymous_cannot_see_reports(client, reported):
    assert client.get("/api/v1/admin/reports").status_code in (401, 403)


def test_profile_exposes_admin_flag(client, db_session, auth_headers):
    assert client.get("/api/v1/profile/me", headers=auth_headers).json()["is_admin"] is False
    _promote(db_session, client, auth_headers)
    assert client.get("/api/v1/profile/me", headers=auth_headers).json()["is_admin"] is True


# ------------------------------------------------------------------ 처리


def test_admin_sees_report_with_target_content(client, db_session, reported, auth_headers):
    """대상 내용이 같이 와야 한다.

    신고만 보고 대상을 다시 찾아 들어가야 하면 처리가 느려지고, 느려지면 안 하게 된다.
    """
    _promote(db_session, client, auth_headers)
    items = client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["reason"] == "spam"
    assert item["target"]["kind"] == "post"
    assert item["target"]["title"] == TITLE
    assert item["target"]["url"] == f"/@author/{reported['slug']}"


def test_resolve_removes_from_queue(client, db_session, reported, auth_headers):
    _promote(db_session, client, auth_headers)
    report_id = client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"][0]["id"]

    r = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=auth_headers,
        json={"status": "rejected"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"
    assert r.json()["unpublished"] is False
    assert client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"] == []


def test_resolve_can_unpublish_the_post(client, db_session, reported, auth_headers):
    """신고가 타당하면 글이 실제로 내려가야 한다.

    큐에서만 지우고 글이 그대로면 신고 처리는 아무 일도 하지 않은 것이다.
    """
    _promote(db_session, client, auth_headers)
    report_id = client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"][0]["id"]

    r = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=auth_headers,
        json={"status": "resolved", "unpublish_post": True},
    )
    assert r.json()["unpublished"] is True
    assert client.get(f"/api/v1/public/posts/author/{reported['slug']}").status_code == 404


def test_resolving_twice_is_not_a_server_error(client, db_session, reported, auth_headers):
    """두 번 눌러도 500 이 나가면 안 된다. 운영자는 두 번 누른다."""
    _promote(db_session, client, auth_headers)
    report_id = client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"][0]["id"]
    body = {"status": "rejected"}
    assert client.post(
        f"/api/v1/admin/reports/{report_id}/resolve", headers=auth_headers, json=body
    ).status_code == 200
    again = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve", headers=auth_headers, json=body
    )
    assert again.status_code == 200

    missing = client.post(
        "/api/v1/admin/reports/does-not-exist/resolve", headers=auth_headers, json=body
    )
    assert missing.status_code == 404


def test_unknown_status_is_rejected(client, db_session, reported, auth_headers):
    _promote(db_session, client, auth_headers)
    report_id = client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"][0]["id"]
    r = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers=auth_headers,
        json={"status": "deleted-everything"},
    )
    assert r.status_code == 422


def test_timestamp_carries_timezone(client, db_session, reported, auth_headers):
    """시각에 시간대 표시가 없으면 브라우저가 현지 시각으로 읽는다.

    실제로 방금 들어온 신고가 화면에 "9시간 전" 으로 보였다.
    운영자가 처리 순서를 정하는 화면에서 시간이 틀리면 화면 자체가 쓸모없다.
    """
    _promote(db_session, client, auth_headers)
    created = client.get("/api/v1/admin/reports", headers=auth_headers).json()["items"][0][
        "created_at"
    ]
    assert datetime.fromisoformat(created).tzinfo is not None

    # 방금 만든 신고다. 시간대를 잘못 붙이면 여기서 몇 시간씩 어긋난다.
    age = abs((datetime.now(timezone.utc) - datetime.fromisoformat(created)).total_seconds())
    assert age < 300, f"{age}초 차이"


def test_summary_counts_pending(client, db_session, reported, auth_headers):
    _promote(db_session, client, auth_headers)
    assert client.get("/api/v1/admin/summary", headers=auth_headers).json()["pending_reports"] == 1
