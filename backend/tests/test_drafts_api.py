"""Draft API — 인증/소유권/자동저장·스냅샷 분리 검증."""

import uuid

import pytest

from src.domain.enums import DraftStatus, SourceType
from src.infrastructure.database.models.draft import Draft
from src.infrastructure.database.models.source import Source


def _make_user_id(client, headers) -> str:
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def _create_source(db_session, user_id: str, content: str = "소스 본문") -> Source:
    source = Source(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=SourceType.RAW,
        origin="raw_text",
        title="테스트 소스",
        content=content,
        extracted_json={},
    )
    db_session.add(source)
    db_session.commit()
    return source


def _create_draft(db_session, user_id: str) -> Draft:
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
    return draft


# ------------------------------------------------------------------ 인증


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/drafts"),
        ("get", "/api/v1/drafts/some-id"),
        ("get", "/api/v1/drafts/some-id/versions"),
        ("get", "/api/v1/export/drafts/some-id/md"),
        ("get", "/api/v1/safety/drafts/some-id/findings"),
        ("post", "/api/v1/safety/drafts/some-id/scan"),
        ("get", "/api/v1/usage/stats"),
        ("get", "/api/v1/jobs/some-id"),
    ],
)
def test_endpoints_require_authentication(client, method, path):
    """예전에는 get_draft / export / safety 가 인증 없이 열려 있었다."""
    response = getattr(client, method)(path)
    assert response.status_code == 401, f"{method.upper()} {path} 가 인증 없이 접근됨"


# ------------------------------------------------------------------ 소유권


def test_cannot_read_another_users_draft(client, db_session, auth_headers, other_auth_headers):
    owner_id = _make_user_id(client, auth_headers)
    draft = _create_draft(db_session, owner_id)

    response = client.get(f"/api/v1/drafts/{draft.id}", headers=other_auth_headers)
    assert response.status_code == 404


def test_cannot_export_another_users_draft(client, db_session, auth_headers, other_auth_headers):
    owner_id = _make_user_id(client, auth_headers)
    draft = _create_draft(db_session, owner_id)

    response = client.get(f"/api/v1/export/drafts/{draft.id}/md", headers=other_auth_headers)
    assert response.status_code == 404


def test_cannot_modify_another_users_draft(client, db_session, auth_headers, other_auth_headers):
    owner_id = _make_user_id(client, auth_headers)
    draft = _create_draft(db_session, owner_id)

    response = client.put(
        f"/api/v1/drafts/{draft.id}/content",
        headers=other_auth_headers,
        json={"content_md": "탈취 시도"},
    )
    assert response.status_code == 404


def test_owner_can_read_own_draft(client, db_session, auth_headers):
    owner_id = _make_user_id(client, auth_headers)
    draft = _create_draft(db_session, owner_id)

    response = client.get(f"/api/v1/drafts/{draft.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == draft.id


# ------------------------------------------------- 자동저장 vs 버전 스냅샷


def test_autosave_updates_in_place_without_creating_versions(client, db_session, auth_headers):
    """예전에는 자동저장 때마다 새 버전이 쌓여 버전 관리가 무의미해졌다."""
    owner_id = _make_user_id(client, auth_headers)
    draft = _create_draft(db_session, owner_id)

    for i in range(5):
        response = client.put(
            f"/api/v1/drafts/{draft.id}/content",
            headers=auth_headers,
            json={"content_md": f"편집 {i}"},
        )
        assert response.status_code == 200

    versions = client.get(f"/api/v1/drafts/{draft.id}/versions", headers=auth_headers).json()
    assert len(versions) == 1
    assert versions[0]["content_md"] == "편집 4"


def test_snapshot_creates_a_new_version(client, db_session, auth_headers):
    owner_id = _make_user_id(client, auth_headers)
    draft = _create_draft(db_session, owner_id)

    client.put(
        f"/api/v1/drafts/{draft.id}/content", headers=auth_headers, json={"content_md": "v1"}
    )
    response = client.post(
        f"/api/v1/drafts/{draft.id}/versions", headers=auth_headers, json={"content_md": "v2"}
    )
    assert response.status_code == 201
    assert response.json()["version_no"] == 2

    versions = client.get(f"/api/v1/drafts/{draft.id}/versions", headers=auth_headers).json()
    assert [v["version_no"] for v in versions] == [2, 1]


def test_snapshot_rejects_identical_content(client, db_session, auth_headers):
    owner_id = _make_user_id(client, auth_headers)
    draft = _create_draft(db_session, owner_id)

    client.put(
        f"/api/v1/drafts/{draft.id}/content", headers=auth_headers, json={"content_md": "같은 내용"}
    )
    response = client.post(
        f"/api/v1/drafts/{draft.id}/versions", headers=auth_headers, json={"content_md": "같은 내용"}
    )
    assert response.status_code == 409


# ------------------------------------------------------------------- 생성


def test_create_draft_rejects_unknown_source(client, auth_headers):
    response = client.post(
        "/api/v1/drafts",
        headers=auth_headers,
        json={
            "source_ids": ["does-not-exist"],
            "type": "implementation",
            "audience": "intermediate",
            "length": "default",
            "use_style_profile": False,
        },
    )
    assert response.status_code == 404


def test_create_draft_rejects_other_users_source(
    client, db_session, auth_headers, other_auth_headers
):
    """남의 소스로 글을 생성할 수 없어야 한다."""
    owner_id = _make_user_id(client, auth_headers)
    source = _create_source(db_session, owner_id)

    response = client.post(
        "/api/v1/drafts",
        headers=other_auth_headers,
        json={
            "source_ids": [source.id],
            "type": "implementation",
            "audience": "intermediate",
            "length": "default",
            "use_style_profile": False,
        },
    )
    assert response.status_code == 404


def test_create_draft_rejects_invalid_type(client, db_session, auth_headers):
    owner_id = _make_user_id(client, auth_headers)
    source = _create_source(db_session, owner_id)

    response = client.post(
        "/api/v1/drafts",
        headers=auth_headers,
        json={
            "source_ids": [source.id],
            "type": "존재하지-않는-타입",
            "audience": "intermediate",
            "length": "default",
            "use_style_profile": False,
        },
    )
    assert response.status_code == 422
