"""템플릿, 발행 예약, 작성 통계.

develop 브랜치에서 온 기능이다. 병합하면서 소유자 확인과 입력 검증을 다시 썼으므로
그 부분을 중점적으로 본다.
"""

from datetime import datetime, timedelta, timezone

import pytest


def register(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password1234", "name": "테스터"},
    )
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_draft(client, token):
    source = client.post("/api/v1/sources/extract", json={"raw_text": "x"}, headers=auth(token))
    return client.post(
        "/api/v1/drafts",
        json={
            "source_ids": [source.json()[0]["id"]],
            "type": "implementation",
            "audience": "intermediate",
            "length": "default",
            "use_style_profile": False,
        },
        headers=auth(token),
    ).json()


def future(hours=24):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


# ------------------------------------------------------------------ 템플릿


def test_템플릿_생성과_조회(client):
    token = register(client, "tpl1@devshiplog.com")
    created = client.post(
        "/api/v1/templates",
        json={
            "name": "트러블슈팅 기본",
            "type": "troubleshooting",
            "audience": "intermediate",
            "length_preset": "default",
        },
        headers=auth(token),
    )
    assert created.status_code == 201, created.text

    listed = client.get("/api/v1/templates", headers=auth(token))
    assert [t["name"] for t in listed.json()] == ["트러블슈팅 기본"]


def test_모르는_유형은_거절된다(client):
    token = register(client, "tpl2@devshiplog.com")
    response = client.post(
        "/api/v1/templates",
        json={
            "name": "이상한 것",
            "type": "존재하지않는유형",
            "audience": "intermediate",
            "length_preset": "default",
        },
        headers=auth(token),
    )
    # 자유 문자열을 받으면 이 템플릿으로 만든 초안이 생성 단계에서 거절된다.
    assert response.status_code == 422


def test_남의_템플릿은_보이지도_지워지지도_않는다(client):
    mine = register(client, "tpl3@devshiplog.com")
    other = register(client, "tpl4@devshiplog.com")

    created = client.post(
        "/api/v1/templates",
        json={
            "name": "내 템플릿",
            "type": "implementation",
            "audience": "beginner",
            "length_preset": "short",
        },
        headers=auth(mine),
    ).json()

    assert client.get(f"/api/v1/templates/{created['id']}", headers=auth(other)).status_code == 404
    assert (
        client.delete(f"/api/v1/templates/{created['id']}", headers=auth(other)).status_code == 404
    )
    # 403 이 아니라 404 여야 한다 — 403 은 "그런 템플릿이 있긴 하다" 를 알려준다.
    assert client.get("/api/v1/templates", headers=auth(other)).json() == []
    # 남이 못 지웠으므로 내 것은 그대로 있다.
    assert client.get(f"/api/v1/templates/{created['id']}", headers=auth(mine)).status_code == 200


def test_남의_문체_프로필은_붙일_수_없다(client, db_session):
    from src.infrastructure.database.models.style_profile import StyleProfile

    mine = register(client, "tpl5@devshiplog.com")
    other_id = client.get(
        "/api/v1/auth/me", headers=auth(register(client, "tpl6@devshiplog.com"))
    ).json()["id"]

    profile = StyleProfile(user_id=other_id, blog_url="https://example.com/blog")
    db_session.add(profile)
    db_session.commit()

    response = client.post(
        "/api/v1/templates",
        json={
            "name": "훔친 문체",
            "type": "implementation",
            "audience": "beginner",
            "length_preset": "short",
            "style_profile_id": profile.id,
        },
        headers=auth(mine),
    )
    assert response.status_code == 404


# --------------------------------------------------------------- 발행 예약


def test_예약_생성과_목록(client):
    token = register(client, "sch1@devshiplog.com")
    draft = make_draft(client, token)

    created = client.post(
        "/api/v1/schedules",
        json={"draft_id": draft["id"], "platform": "notion", "scheduled_at": future()},
        headers=auth(token),
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending"

    listed = client.get("/api/v1/schedules", headers=auth(token))
    assert len(listed.json()) == 1


def test_남의_초안은_예약할_수_없다(client):
    owner = register(client, "sch2@devshiplog.com")
    attacker = register(client, "sch3@devshiplog.com")
    draft = make_draft(client, owner)

    response = client.post(
        "/api/v1/schedules",
        json={"draft_id": draft["id"], "platform": "notion", "scheduled_at": future()},
        headers=auth(attacker),
    )
    assert response.status_code == 404


def test_과거_시각은_거절된다(client):
    token = register(client, "sch4@devshiplog.com")
    draft = make_draft(client, token)

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    response = client.post(
        "/api/v1/schedules",
        json={"draft_id": draft["id"], "platform": "notion", "scheduled_at": past},
        headers=auth(token),
    )
    assert response.status_code == 422


@pytest.mark.parametrize("value", ["어제", "2026-13-45T99:99:99", ""])
def test_형식이_틀린_시각은_거절된다(client, value):
    token = register(client, f"sch5{len(value)}@devshiplog.com")
    draft = make_draft(client, token)
    response = client.post(
        "/api/v1/schedules",
        json={"draft_id": draft["id"], "platform": "notion", "scheduled_at": value},
        headers=auth(token),
    )
    assert response.status_code == 422


def test_모르는_플랫폼은_거절된다(client):
    token = register(client, "sch6@devshiplog.com")
    draft = make_draft(client, token)
    response = client.post(
        "/api/v1/schedules",
        json={"draft_id": draft["id"], "platform": "마이스페이스", "scheduled_at": future()},
        headers=auth(token),
    )
    assert response.status_code == 422


def test_남의_예약은_지울_수_없다(client):
    owner = register(client, "sch7@devshiplog.com")
    attacker = register(client, "sch8@devshiplog.com")
    draft = make_draft(client, owner)
    created = client.post(
        "/api/v1/schedules",
        json={"draft_id": draft["id"], "platform": "medium", "scheduled_at": future()},
        headers=auth(owner),
    ).json()

    assert (
        client.delete(f"/api/v1/schedules/{created['id']}", headers=auth(attacker)).status_code
        == 404
    )
    assert len(client.get("/api/v1/schedules", headers=auth(owner)).json()) == 1


# ------------------------------------------------------------- 초안 메타데이터


def test_태그_메모_체크리스트_갱신(client):
    token = register(client, "meta1@devshiplog.com")
    draft = make_draft(client, token)

    response = client.patch(
        f"/api/v1/drafts/{draft['id']}",
        json={"tags": ["redis", "성능"], "notes": "벤치마크 다시"},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["tags"] == ["redis", "성능"]

    # 보내지 않은 항목은 그대로여야 한다.
    response = client.patch(
        f"/api/v1/drafts/{draft['id']}",
        json={"notes": "수정함"},
        headers=auth(token),
    )
    assert response.json()["tags"] == ["redis", "성능"]
    assert response.json()["notes"] == "수정함"


def test_남의_초안은_고칠_수도_지울_수도_없다(client):
    owner = register(client, "meta2@devshiplog.com")
    attacker = register(client, "meta3@devshiplog.com")
    draft = make_draft(client, owner)

    assert (
        client.patch(
            f"/api/v1/drafts/{draft['id']}", json={"notes": "훔침"}, headers=auth(attacker)
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/drafts/{draft['id']}", headers=auth(attacker)).status_code == 404
    assert client.get(f"/api/v1/drafts/{draft['id']}", headers=auth(owner)).status_code == 200


def test_소유자가_아닌_컬럼은_갱신되지_않는다(client):
    """**fields 를 그대로 setattr 하면 user_id 까지 바뀐다."""
    token = register(client, "meta4@devshiplog.com")
    attacker_id = client.get(
        "/api/v1/auth/me", headers=auth(register(client, "meta5@devshiplog.com"))
    ).json()["id"]
    draft = make_draft(client, token)

    client.patch(
        f"/api/v1/drafts/{draft['id']}",
        json={"notes": "정상", "user_id": attacker_id},
        headers=auth(token),
    )
    # 여전히 내 것이어야 한다.
    assert client.get(f"/api/v1/drafts/{draft['id']}", headers=auth(token)).status_code == 200


def test_초안을_지워도_발행한_글은_남는다(client):
    token = register(client, "meta6@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "metawriter"}, headers=auth(token))
    draft = make_draft(client, token)
    client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "본문입니다. " * 12},
        headers=auth(token),
    )
    post = client.post(
        "/api/v1/posts",
        json={"draft_id": draft["id"], "title": "남아야 하는 글"},
        headers=auth(token),
    ).json()

    assert client.delete(f"/api/v1/drafts/{draft['id']}", headers=auth(token)).status_code == 200
    # 발행물은 발행 시점의 스냅샷이다. 독자가 읽던 글이 없어지면 안 된다.
    assert (
        client.get(f"/api/v1/public/blogs/metawriter/posts/{post['slug']}").status_code == 200
    )


# ------------------------------------------------------------------ 통계


def test_통계는_내_초안만_센다(client):
    mine = register(client, "an1@devshiplog.com")
    other = register(client, "an2@devshiplog.com")
    make_draft(client, mine)
    make_draft(client, other)
    make_draft(client, other)

    stats = client.get("/api/v1/analytics/drafts", headers=auth(mine)).json()
    assert stats["total"] == 1


def test_초안이_없으면_0_으로_답한다(client):
    token = register(client, "an3@devshiplog.com")
    stats = client.get("/api/v1/analytics/drafts", headers=auth(token)).json()
    assert stats["total"] == 0
    assert stats["average_length"] == 0
    assert stats["style_profile_usage_rate"] == 0

    patterns = client.get("/api/v1/analytics/writing-patterns", headers=auth(token)).json()
    assert patterns["most_used_type"] == "none"


def test_평균_길이는_실제_글자수로_센다(client):
    """프리셋에서 추측한 값이 아니라 정말 쓴 글자 수여야 한다."""
    token = register(client, "an4@devshiplog.com")
    draft = make_draft(client, token)
    client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "가" * 500},
        headers=auth(token),
    )

    stats = client.get("/api/v1/analytics/drafts", headers=auth(token)).json()
    assert stats["average_length"] == 500


def test_시간대_분포(client):
    token = register(client, "an5@devshiplog.com")
    make_draft(client, token)
    body = client.get("/api/v1/analytics/time-distribution", headers=auth(token)).json()
    assert sum(body["by_hour"].values()) == 1
    assert sum(body["by_day_of_week"].values()) == 1
