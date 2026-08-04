"""블로그 플랫폼 E2E: 신원 → 발행 → 공개 읽기 → 소셜 → 모더레이션."""

import uuid

import pytest

from src.domain.enums import DraftStatus
from src.infrastructure.database.models.draft import Draft


# ----------------------------------------------------------------- 픽스처


def _make_draft(db_session, user_id: str, content: str = None) -> str:
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
    return draft.id


def _uid(client, headers) -> str:
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def _set_handle(client, headers, handle: str):
    return client.put("/api/v1/profile/me", headers=headers, json={"handle": handle})


def _write_and_publish(client, db_session, headers, title, body, tags=(), handle=None):
    """작업본을 만들고 내용을 채운 뒤 발행한다."""
    user_id = _uid(client, headers)
    draft_id = _make_draft(db_session, user_id)
    client.put(
        f"/api/v1/drafts/{draft_id}/content", headers=headers, json={"content_md": body}
    )
    return client.post(
        "/api/v1/posts",
        headers=headers,
        json={"draft_id": draft_id, "title": title, "tags": list(tags)},
    )


BODY = "이 글은 발행 테스트를 위한 본문입니다. 최소 길이를 넘기기 위해 충분히 길게 씁니다."


# ------------------------------------------------------------- 블로그 신원


def test_handle_required_before_publishing(client, db_session, auth_headers):
    """공개 주소가 /@handle/slug 라서 handle 없이는 URL 자체를 만들 수 없다."""
    r = _write_and_publish(client, db_session, auth_headers, "제목", BODY)
    assert r.status_code == 422
    assert "아이디" in r.json()["detail"]


def test_set_and_check_handle(client, auth_headers):
    assert client.get(
        "/api/v1/profile/handle-available?handle=thoh", headers=auth_headers
    ).json()["available"]

    assert _set_handle(client, auth_headers, "Thoh").status_code == 200
    assert client.get("/api/v1/profile/me", headers=auth_headers).json()["handle"] == "thoh"


def test_handle_conflict(client, auth_headers, other_auth_headers):
    _set_handle(client, auth_headers, "taken")
    r = _set_handle(client, other_auth_headers, "taken")
    assert r.status_code == 422
    assert client.get(
        "/api/v1/profile/handle-available?handle=taken", headers=other_auth_headers
    ).json()["available"] is False


@pytest.mark.parametrize("bad", ["ad", "admin", "-nope", "한글"])
def test_invalid_handles_rejected_by_api(client, auth_headers, bad):
    assert _set_handle(client, auth_headers, bad).status_code == 422


def test_needs_handle_flag(client, auth_headers):
    assert client.get("/api/v1/profile/me", headers=auth_headers).json()["needs_handle"]
    _set_handle(client, auth_headers, "writer")
    assert not client.get("/api/v1/profile/me", headers=auth_headers).json()["needs_handle"]


# ----------------------------------------------------------------- 발행


def test_publish_creates_public_post(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    r = _write_and_publish(
        client, db_session, auth_headers, "리액트 렌더링 최적화", BODY, tags=["React", "성능"]
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["url"] == "/@thoh/리액트-렌더링-최적화"
    assert body["created"] is True
    assert set(body["tags"]) == {"React", "성능"}


def test_publish_blocks_on_sensitive_content(client, db_session, auth_headers):
    """공개는 되돌릴 수 없다. 민감정보가 있으면 기본적으로 막는다."""
    _set_handle(client, auth_headers, "thoh")
    leaky = BODY + "\napi_key = sk-abcdefghijklmnopqrstuvwxyz1234567890"
    r = _write_and_publish(client, db_session, auth_headers, "실수", leaky)
    assert r.status_code == 422
    assert "민감정보" in r.json()["detail"]


def test_publish_allows_sensitive_with_explicit_consent(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    user_id = _uid(client, auth_headers)
    draft_id = _make_draft(db_session, user_id)
    leaky = BODY + "\napi_key = sk-abcdefghijklmnopqrstuvwxyz1234567890"
    client.put(f"/api/v1/drafts/{draft_id}/content", headers=auth_headers, json={"content_md": leaky})

    r = client.post(
        "/api/v1/posts",
        headers=auth_headers,
        json={"draft_id": draft_id, "title": "확인함", "allow_sensitive": True},
    )
    assert r.status_code == 201
    assert r.json()["sensitive_findings"] >= 1


def test_republish_keeps_url(client, db_session, auth_headers):
    """주소가 바뀌면 이미 걸린 링크와 검색 색인이 전부 깨진다."""
    _set_handle(client, auth_headers, "thoh")
    user_id = _uid(client, auth_headers)
    draft_id = _make_draft(db_session, user_id)
    client.put(f"/api/v1/drafts/{draft_id}/content", headers=auth_headers, json={"content_md": BODY})

    first = client.post(
        "/api/v1/posts", headers=auth_headers, json={"draft_id": draft_id, "title": "원래 제목"}
    ).json()

    client.put(
        f"/api/v1/drafts/{draft_id}/content",
        headers=auth_headers,
        json={"content_md": BODY + " 내용을 고쳤습니다."},
    )
    second = client.post(
        "/api/v1/posts", headers=auth_headers, json={"draft_id": draft_id, "title": "제목도 바꿈"}
    ).json()

    assert second["created"] is False
    assert second["slug"] == first["slug"]


def test_duplicate_titles_get_distinct_slugs(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    a = _write_and_publish(client, db_session, auth_headers, "같은 제목", BODY).json()
    b = _write_and_publish(client, db_session, auth_headers, "같은 제목", BODY).json()
    assert a["slug"] != b["slug"]


def test_short_body_rejected(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    r = _write_and_publish(client, db_session, auth_headers, "짧음", "짧다")
    assert r.status_code == 422


# ------------------------------------------------------------ 공개 읽기


def test_public_endpoints_need_no_auth(client, db_session, auth_headers):
    """검색 크롤러는 로그인하지 않는다. 이 경로들이 401 이면 색인 자체가 안 된다."""
    _set_handle(client, auth_headers, "thoh")
    published = _write_and_publish(client, db_session, auth_headers, "공개 글", BODY).json()

    assert client.get("/api/v1/public/feed").status_code == 200
    assert client.get("/api/v1/public/blogs/thoh").status_code == 200
    assert client.get("/api/v1/public/blogs/thoh/posts").status_code == 200
    r = client.get(f"/api/v1/public/blogs/thoh/posts/{published['slug']}")
    assert r.status_code == 200
    assert r.json()["content_md"].startswith("이 글은")


def test_public_response_hides_email(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    _write_and_publish(client, db_session, auth_headers, "공개 글", BODY)
    payload = client.get("/api/v1/public/blogs/thoh").text
    assert "devshiplog.com" not in payload or "@devshiplog.com" not in payload


def test_unpublished_post_is_not_public(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    published = _write_and_publish(client, db_session, auth_headers, "내릴 글", BODY).json()
    client.post(f"/api/v1/posts/{published['id']}/unpublish", headers=auth_headers)

    assert client.get(f"/api/v1/public/blogs/thoh/posts/{published['slug']}").status_code == 404
    assert client.get("/api/v1/public/feed").json()["items"] == []


def test_unknown_blog_returns_404(client):
    assert client.get("/api/v1/public/blogs/nobody").status_code == 404


def test_feed_and_tag_filter(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    _write_and_publish(client, db_session, auth_headers, "리액트 글", BODY, tags=["react"])
    _write_and_publish(client, db_session, auth_headers, "파이썬 글", BODY, tags=["python"])

    assert len(client.get("/api/v1/public/feed").json()["items"]) == 2
    only_react = client.get("/api/v1/public/feed?tag=react").json()["items"]
    assert len(only_react) == 1 and only_react[0]["title"] == "리액트 글"

    tags = {t["name"] for t in client.get("/api/v1/public/tags").json()}
    assert {"react", "python"} <= tags


def test_search(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    _write_and_publish(client, db_session, auth_headers, "고유한제목 검색용", BODY)
    found = client.get("/api/v1/public/search?q=고유한제목").json()["items"]
    assert len(found) == 1


def test_sitemap_lists_published_urls(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    p = _write_and_publish(client, db_session, auth_headers, "색인될 글", BODY).json()
    urls = [row["url"] for row in client.get("/api/v1/public/sitemap").json()]
    assert p["url"] in urls


def test_rss_source(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "thoh")
    _write_and_publish(client, db_session, auth_headers, "피드 글", BODY)
    rss = client.get("/api/v1/public/blogs/thoh/rss").json()
    assert rss["author"]["handle"] == "thoh"
    assert rss["items"][0]["title"] == "피드 글"


# ------------------------------------------------------------------ 소셜


def _two_bloggers(client, db_session, auth_headers, other_auth_headers):
    _set_handle(client, auth_headers, "author")
    _set_handle(client, other_auth_headers, "reader")
    post = _write_and_publish(client, db_session, auth_headers, "소셜 대상 글", BODY).json()
    return post


def test_like_toggles_and_counts(client, db_session, auth_headers, other_auth_headers):
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)

    on = client.post(f"/api/v1/social/posts/{post['id']}/like", headers=other_auth_headers).json()
    assert on == {"liked": True, "like_count": 1}

    off = client.post(f"/api/v1/social/posts/{post['id']}/like", headers=other_auth_headers).json()
    assert off == {"liked": False, "like_count": 0}


def test_comment_thread_and_reply_depth(client, db_session, auth_headers, other_auth_headers):
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)

    root = client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=other_auth_headers,
        json={"body": "좋은 글이네요"},
    )
    assert root.status_code == 201
    root_id = root.json()["id"]

    reply = client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=auth_headers,
        json={"body": "감사합니다", "parent_id": root_id},
    )
    assert reply.status_code == 201

    # 답글의 답글은 막는다 (모바일에서 읽히지 않는다)
    nested = client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=other_auth_headers,
        json={"body": "더 깊이", "parent_id": reply.json()["id"]},
    )
    assert nested.status_code == 422

    detail = client.get(f"/api/v1/public/blogs/author/posts/{post['slug']}").json()
    assert detail["comment_count"] == 2
    assert len(detail["comments"]) == 1
    assert len(detail["comments"][0]["replies"]) == 1


def test_deleted_comment_keeps_thread(client, db_session, auth_headers, other_auth_headers):
    """답글이 달린 댓글을 실제로 지우면 대화 흐름이 끊긴다."""
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)
    root_id = client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=other_auth_headers,
        json={"body": "원 댓글"},
    ).json()["id"]
    client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=auth_headers,
        json={"body": "답글", "parent_id": root_id},
    )

    assert client.delete(f"/api/v1/social/comments/{root_id}", headers=other_auth_headers).status_code == 200

    detail = client.get(f"/api/v1/public/blogs/author/posts/{post['slug']}").json()
    assert detail["comments"][0]["deleted"] is True
    assert detail["comments"][0]["body"] is None
    assert len(detail["comments"][0]["replies"]) == 1  # 답글은 남는다


def test_post_author_can_delete_others_comment(client, db_session, auth_headers, other_auth_headers):
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)
    cid = client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=other_auth_headers,
        json={"body": "스팸"},
    ).json()["id"]
    # 글쓴이가 자기 글의 댓글을 지울 수 있어야 한다
    assert client.delete(f"/api/v1/social/comments/{cid}", headers=auth_headers).status_code == 200


def test_follow_toggles_and_feed(client, db_session, auth_headers, other_auth_headers):
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)

    on = client.post("/api/v1/social/users/author/follow", headers=other_auth_headers).json()
    assert on == {"following": True, "follower_count": 1}

    feed = client.get("/api/v1/social/feed/following", headers=other_auth_headers).json()
    assert [i["title"] for i in feed["items"]] == ["소셜 대상 글"]

    off = client.post("/api/v1/social/users/author/follow", headers=other_auth_headers).json()
    assert off == {"following": False, "follower_count": 0}
    assert client.get("/api/v1/social/feed/following", headers=other_auth_headers).json()["items"] == []


def test_cannot_follow_self(client, auth_headers):
    _set_handle(client, auth_headers, "author")
    assert client.post("/api/v1/social/users/author/follow", headers=auth_headers).status_code == 422


def test_notifications_created_and_read(client, db_session, auth_headers, other_auth_headers):
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)
    client.post(f"/api/v1/social/posts/{post['id']}/like", headers=other_auth_headers)
    client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=other_auth_headers,
        json={"body": "댓글"},
    )
    client.post("/api/v1/social/users/author/follow", headers=other_auth_headers)

    box = client.get("/api/v1/social/notifications", headers=auth_headers).json()
    assert box["unread_count"] == 3
    assert {n["type"] for n in box["items"]} == {"like", "comment", "follow"}

    client.post("/api/v1/social/notifications/read", headers=auth_headers)
    assert client.get("/api/v1/social/notifications", headers=auth_headers).json()["unread_count"] == 0


def test_no_self_notification(client, db_session, auth_headers):
    """내 글에 내가 좋아요를 눌렀다고 알림이 오면 안 된다."""
    _set_handle(client, auth_headers, "author")
    post = _write_and_publish(client, db_session, auth_headers, "내 글", BODY).json()
    client.post(f"/api/v1/social/posts/{post['id']}/like", headers=auth_headers)
    assert client.get("/api/v1/social/notifications", headers=auth_headers).json()["unread_count"] == 0


# ------------------------------------------------------------ 모더레이션


def test_report_and_dedup(client, db_session, auth_headers, other_auth_headers):
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)
    payload = {"target_type": "post", "target_id": post["id"], "reason": "spam"}

    first = client.post("/api/v1/social/reports", headers=other_auth_headers, json=payload).json()
    assert first["reported"] and not first["already"]

    # 같은 사람이 같은 대상을 또 신고해도 큐가 부풀지 않는다
    again = client.post("/api/v1/social/reports", headers=other_auth_headers, json=payload).json()
    assert again["already"] is True


def test_cannot_report_own_content(client, db_session, auth_headers):
    _set_handle(client, auth_headers, "author")
    post = _write_and_publish(client, db_session, auth_headers, "내 글", BODY).json()
    r = client.post(
        "/api/v1/social/reports",
        headers=auth_headers,
        json={"target_type": "post", "target_id": post["id"], "reason": "spam"},
    )
    assert r.status_code == 422


def test_block_hides_commenting(client, db_session, auth_headers, other_auth_headers):
    post = _two_bloggers(client, db_session, auth_headers, other_auth_headers)

    assert client.post("/api/v1/social/users/reader/block", headers=auth_headers).json()["blocked"]

    blocked = client.post(
        f"/api/v1/social/posts/{post['id']}/comments",
        headers=other_auth_headers,
        json={"body": "댓글 시도"},
    )
    assert blocked.status_code == 403


def test_publish_requires_auth(client):
    assert client.post("/api/v1/posts", json={"draft_id": "x", "title": "y"}).status_code == 401
    assert client.get("/api/v1/profile/me").status_code == 401
    assert client.get("/api/v1/social/notifications").status_code == 401


def test_cannot_publish_others_draft(client, db_session, auth_headers, other_auth_headers):
    _set_handle(client, auth_headers, "author")
    _set_handle(client, other_auth_headers, "reader")
    owner_id = _uid(client, auth_headers)
    draft_id = _make_draft(db_session, owner_id)
    client.put(f"/api/v1/drafts/{draft_id}/content", headers=auth_headers, json={"content_md": BODY})

    r = client.post(
        "/api/v1/posts", headers=other_auth_headers, json={"draft_id": draft_id, "title": "탈취"}
    )
    assert r.status_code == 404
