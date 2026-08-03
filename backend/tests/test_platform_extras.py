"""비밀번호 재설정, 자동저장 충돌, 조회수 중복 제거, 시리즈 네비게이션."""

import time

import pytest


def register(client, email="extra@devshiplog.com", password="password1234"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "테스터"},
    )
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_post(client, token, title="테스트 글", body=None):
    body = body or "본문입니다. " * 12
    source = client.post("/api/v1/sources/extract", json={"raw_text": "x"}, headers=auth(token))
    draft = client.post(
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
    client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": body},
        headers=auth(token),
    )
    post = client.post(
        "/api/v1/posts",
        json={"draft_id": draft["id"], "title": title, "tags": ["테스트"]},
        headers=auth(token),
    )
    return draft, post.json()


# --------------------------------------------------------------- 비밀번호 재설정


def test_재설정_요청은_가입_여부를_드러내지_않는다(client):
    register(client, "reset1@devshiplog.com")

    known = client.post("/api/v1/auth/password-reset", json={"email": "reset1@devshiplog.com"})
    unknown = client.post("/api/v1/auth/password-reset", json={"email": "nobody@devshiplog.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


def test_토큰으로_비밀번호를_바꾸고_새_비밀번호로_로그인된다(client, db_session):
    from src.application.use_cases.auth.password_reset import RequestPasswordResetUseCase
    from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl

    email = "reset2@devshiplog.com"
    register(client, email)

    token = RequestPasswordResetUseCase(db_session, UserRepositoryImpl(db_session)).execute(email)
    assert token

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "brandnew1234"},
    )
    assert response.status_code == 200

    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": "brandnew1234"}
    ).status_code == 200
    # 옛 비밀번호는 더 이상 통하지 않아야 한다.
    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password1234"}
    ).status_code == 401


def test_같은_토큰은_두_번_쓸_수_없다(client, db_session):
    from src.application.use_cases.auth.password_reset import RequestPasswordResetUseCase
    from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl

    email = "reset3@devshiplog.com"
    register(client, email)
    token = RequestPasswordResetUseCase(db_session, UserRepositoryImpl(db_session)).execute(email)

    client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "firstchange1234"},
    )
    again = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "secondchange1234"},
    )
    assert again.status_code == 422


def test_위조_토큰은_거절된다(client):
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "x" * 40, "new_password": "whatever1234"},
    )
    assert response.status_code == 422


def test_새_요청은_이전_토큰을_무효화한다(client, db_session):
    from src.application.use_cases.auth.password_reset import RequestPasswordResetUseCase
    from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl

    email = "reset4@devshiplog.com"
    register(client, email)
    use_case = RequestPasswordResetUseCase(db_session, UserRepositoryImpl(db_session))

    old = use_case.execute(email)
    new = use_case.execute(email)

    assert client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": old, "new_password": "shouldfail1234"},
    ).status_code == 422
    assert client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": new, "new_password": "shouldwork1234"},
    ).status_code == 200


# ----------------------------------------------------------------- 자동저장 충돌


def test_revision_이_맞으면_저장된다(client):
    token = register(client, "lock1@devshiplog.com")
    draft, _ = make_post(client, token)

    first = client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "첫 번째 저장입니다. " * 5},
        headers=auth(token),
    ).json()

    second = client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "두 번째 저장입니다. " * 5, "base_revision": first["revision"]},
        headers=auth(token),
    )
    assert second.status_code == 200
    assert second.json()["revision"] == first["revision"] + 1


def test_사이에_다른_저장이_있으면_409(client):
    token = register(client, "lock2@devshiplog.com")
    draft, _ = make_post(client, token)

    a = client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "A 탭이 읽은 내용. " * 5},
        headers=auth(token),
    ).json()

    # B 탭이 먼저 저장한다.
    client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "B 탭이 쓴 내용입니다. " * 5, "base_revision": a["revision"]},
        headers=auth(token),
    )

    # A 탭이 옛 revision 으로 저장을 시도한다.
    conflict = client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "A 탭이 쓴 내용입니다. " * 5, "base_revision": a["revision"]},
        headers=auth(token),
    )
    assert conflict.status_code == 409
    body = conflict.json()
    # 사용자가 고르려면 상대가 무엇을 썼는지 볼 수 있어야 한다.
    assert "B 탭이 쓴 내용입니다." in body["current_content_md"]
    assert body["current_revision"] > a["revision"]


def test_base_revision_을_안_보내면_기존처럼_덮어쓴다(client):
    """기존 클라이언트를 깨지 않아야 한다."""
    token = register(client, "lock3@devshiplog.com")
    draft, _ = make_post(client, token)

    client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "먼저 쓴 내용. " * 5},
        headers=auth(token),
    )
    response = client.put(
        f"/api/v1/drafts/{draft['id']}/content",
        json={"content_md": "나중에 쓴 내용. " * 5},
        headers=auth(token),
    )
    assert response.status_code == 200


# ------------------------------------------------------------------- 조회수


def test_같은_사람의_새로고침은_조회수를_올리지_않는다(client):
    token = register(client, "view1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "viewer1"}, headers=auth(token))
    _, post = make_post(client, token, title="조회수 검증")

    url = f"/api/v1/public/blogs/viewer1/posts/{post['slug']}"
    first = client.get(url).json()["view_count"]
    second = client.get(url).json()["view_count"]
    third = client.get(url).json()["view_count"]

    assert first == 1
    assert second == third == 1


def test_다른_뷰어는_따로_센다(client):
    token = register(client, "view2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "viewer2"}, headers=auth(token))
    _, post = make_post(client, token, title="다른 뷰어")

    url = f"/api/v1/public/blogs/viewer2/posts/{post['slug']}"
    client.get(url, headers={"User-Agent": "browser-A"})
    body = client.get(url, headers={"User-Agent": "completely-different-browser-B"}).json()

    assert body["view_count"] == 2


# ---------------------------------------------------------------- 시리즈 네비


@pytest.fixture
def series_setup(client):
    token = register(client, "series1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "serieswriter"}, headers=auth(token))

    series = client.post(
        "/api/v1/series", json={"name": "연재물", "description": ""}, headers=auth(token)
    )
    posts = []
    for i in range(1, 4):
        _, post = make_post(client, token, title=f"{i}편")
        client.post(
            f"/api/v1/series/{series.json()['id']}/posts",
            json={"post_id": post["id"]},
            headers=auth(token),
        )
        posts.append(post)
        time.sleep(0.01)  # published_at 이 같은 초에 몰리지 않게
    return token, series.json(), posts


def test_시리즈_중간_글은_앞뒤를_모두_가진다(client, series_setup):
    _, _, posts = series_setup
    body = client.get(f"/api/v1/public/blogs/serieswriter/posts/{posts[1]['slug']}").json()

    assert body["series"]["position"] == 2
    assert body["series"]["total"] == 3
    assert body["series"]["previous"]["title"] == "1편"
    assert body["series"]["next"]["title"] == "3편"


def test_첫_글은_이전이_없다(client, series_setup):
    _, _, posts = series_setup
    series = client.get(f"/api/v1/public/blogs/serieswriter/posts/{posts[0]['slug']}").json()[
        "series"
    ]
    assert series["previous"] is None and series["next"]["title"] == "2편"


def test_마지막_글은_다음이_없다(client, series_setup):
    _, _, posts = series_setup
    series = client.get(f"/api/v1/public/blogs/serieswriter/posts/{posts[2]['slug']}").json()[
        "series"
    ]
    assert series["next"] is None and series["previous"]["title"] == "2편"


def test_시리즈에_없는_글은_series_가_null(client):
    token = register(client, "noseries@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "noseries"}, headers=auth(token))
    _, post = make_post(client, token, title="혼자 있는 글")

    body = client.get(f"/api/v1/public/blogs/noseries/posts/{post['slug']}").json()
    assert body["series"] is None


def test_중간_글을_내리면_번호가_건너뛰지_않는다(client, series_setup):
    """3편을 읽는 사람에게 '3 / 3' 이 아니라 '2 / 2' 로 보여야 한다."""
    token, _, posts = series_setup
    client.post(f"/api/v1/posts/{posts[1]['id']}/unpublish", headers=auth(token))

    series = client.get(f"/api/v1/public/blogs/serieswriter/posts/{posts[2]['slug']}").json()[
        "series"
    ]
    assert series["position"] == 2
    assert series["total"] == 2
    assert series["previous"]["title"] == "1편"


# -------------------------------------------------------------------- 커버 검증


def test_javascript_스킴_커버는_거절된다(client):
    token = register(client, "cover1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "coverwriter"}, headers=auth(token))
    draft, _ = make_post(client, token)

    response = client.post(
        "/api/v1/posts",
        json={
            "draft_id": draft["id"],
            "title": "나쁜 커버",
            "cover_url": "javascript:alert(1)",
        },
        headers=auth(token),
    )
    assert response.status_code == 422


def test_우리_업로드_경로와_https_는_허용된다(client):
    token = register(client, "cover2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "coverwriter2"}, headers=auth(token))
    draft, _ = make_post(client, token)

    for url in ("/uploads/posts/abc.png", "https://cdn.example.com/a.png"):
        response = client.post(
            "/api/v1/posts",
            json={"draft_id": draft["id"], "title": "좋은 커버", "cover_url": url},
            headers=auth(token),
        )
        assert response.status_code == 201, url
        assert response.json()["cover_url"] == url
