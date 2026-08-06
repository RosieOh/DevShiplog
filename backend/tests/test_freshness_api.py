"""스택·검증·독자 신호 API."""

from datetime import datetime, timedelta, timezone


def register(client, email):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password1234", "name": "테스터"},
    ).json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


BODY = """## 배경

React 18 에서 겪은 문제입니다.

```json
{ "dependencies": { "react": "^18.3.1" } }
```

본문이 충분히 길어야 발행이 됩니다. """ + "설명입니다. " * 10


def publish(client, token, title="테스트 글", body=BODY, stacks=None):
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
        f"/api/v1/drafts/{draft['id']}/content", json={"content_md": body}, headers=auth(token)
    )
    payload = {"draft_id": draft["id"], "title": title}
    if stacks is not None:
        payload["stacks"] = stacks
    return draft, client.post("/api/v1/posts", json=payload, headers=auth(token)).json()


# ---------------------------------------------------------------- 스택


def test_발행하면_본문에서_스택을_뽑아_붙인다(client):
    token = register(client, "st1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "stackwriter"}, headers=auth(token))
    _, post = publish(client, token)

    names = {s["name"]: s["version"] for s in post["stacks"]}
    assert names["react"] == "18.3"


def test_작성자가_준_스택이_자동_추출을_이긴다(client):
    """자동 추출은 제안이고 확정은 작성자가 한다."""
    token = register(client, "st2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "stackwriter2"}, headers=auth(token))
    _, post = publish(client, token, stacks=[{"name": "vue", "version": "3.4"}])

    assert [(s["name"], s["version"]) for s in post["stacks"]] == [("vue", "3.4")]


def test_모르는_이름은_저장하지_않는다(client):
    token = register(client, "st3@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "stackwriter3"}, headers=auth(token))
    _, post = publish(client, token, stacks=[{"name": "우리회사내부툴", "version": "1"}])
    assert post["stacks"] == []


def test_스택_제안_엔드포인트(client):
    token = register(client, "st4@devshiplog.com")
    response = client.post(
        "/api/v1/posts/stacks/suggest",
        json={"content_md": "```python\nimport fastapi\n```"},
        headers=auth(token),
    )
    assert response.status_code == 200
    names = {s["name"] for s in response.json()["stacks"]}
    assert "python" in names
    # 어디서 찾았는지 알려줘야 작성자가 "이건 아닌데" 를 판단할 수 있다.
    assert all("evidence" in s for s in response.json()["stacks"])


def test_스택_교체는_통째로(client):
    token = register(client, "st5@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "stackwriter5"}, headers=auth(token))
    _, post = publish(client, token)

    response = client.put(
        f"/api/v1/posts/{post['id']}/stacks",
        json=[{"name": "go", "version": "1.23"}],
        headers=auth(token),
    )
    assert [(s["name"], s["version"]) for s in response.json()["stacks"]] == [("go", "1.23")]


def test_남의_글_스택은_못_고친다(client):
    owner = register(client, "st6@devshiplog.com")
    attacker = register(client, "st7@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "stackwriter6"}, headers=auth(owner))
    _, post = publish(client, owner)

    response = client.put(
        f"/api/v1/posts/{post['id']}/stacks",
        json=[{"name": "go", "version": "1"}],
        headers=auth(attacker),
    )
    assert response.status_code == 404


def test_이상한_버전은_거절(client):
    token = register(client, "st8@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "stackwriter8"}, headers=auth(token))
    _, post = publish(client, token)

    response = client.put(
        f"/api/v1/posts/{post['id']}/stacks",
        json=[{"name": "react", "version": "최신"}],
        headers=auth(token),
    )
    assert response.status_code == 422


# ---------------------------------------------------------------- 검증


def test_검증하면_공개_페이지에_반영된다(client):
    token = register(client, "vf1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "verifier"}, headers=auth(token))
    _, post = publish(client, token)

    before = client.get(f"/api/v1/public/blogs/verifier/posts/{post['slug']}").json()
    assert before["freshness"]["verified_at"] is None

    assert client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(token)).status_code == 200

    after = client.get(f"/api/v1/public/blogs/verifier/posts/{post['slug']}").json()
    assert after["freshness"]["verified_at"] is not None


def test_남의_글은_검증할_수_없다(client):
    owner = register(client, "vf2@devshiplog.com")
    attacker = register(client, "vf3@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "verifier2"}, headers=auth(owner))
    _, post = publish(client, owner)

    assert (
        client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(attacker)).status_code == 404
    )


def test_검증하면_밀린_신호가_처리된다(client, db_session):
    """안 그러면 갱신 목록에 영원히 남는다."""
    owner = register(client, "vf4@devshiplog.com")
    reader = register(client, "vf5@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "verifier4"}, headers=auth(owner))
    # 최신 스택으로 발행한다. React 18 로 두면 검증해도 "메이저가 뒤처짐" 으로 남는다.
    _, post = publish(client, owner, stacks=[{"name": "react", "version": "19.0"}])

    client.post(
        f"/api/v1/posts/{post['id']}/signal", json={"kind": "broken"}, headers=auth(reader)
    )
    assert client.get("/api/v1/posts/needs-update", headers=auth(owner)).json()["items"]

    client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(owner))
    assert client.get("/api/v1/posts/needs-update", headers=auth(owner)).json()["items"] == []


# ---------------------------------------------------------------- 독자 신호


def test_신호를_보내면_집계된다(client):
    owner = register(client, "sg1@devshiplog.com")
    reader = register(client, "sg2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "signalwriter"}, headers=auth(owner))
    _, post = publish(client, owner)

    response = client.post(
        f"/api/v1/posts/{post['id']}/signal",
        json={"kind": "works"},
        headers=auth(reader),
    )
    assert response.json() == {"works": 1, "broken": 0, "my_signal": "works"}


def test_같은_사람이_다시_보내면_덮어쓴다(client):
    """마음이 바뀔 수 있다(다시 해보니 됐다). 수를 부풀리면 안 된다."""
    owner = register(client, "sg3@devshiplog.com")
    reader = register(client, "sg4@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "signalwriter3"}, headers=auth(owner))
    _, post = publish(client, owner)

    client.post(f"/api/v1/posts/{post['id']}/signal", json={"kind": "broken"}, headers=auth(reader))
    final = client.post(
        f"/api/v1/posts/{post['id']}/signal", json={"kind": "works"}, headers=auth(reader)
    ).json()

    assert final == {"works": 1, "broken": 0, "my_signal": "works"}


def test_자기_글에는_신호를_못_보낸다(client):
    token = register(client, "sg5@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "signalwriter5"}, headers=auth(token))
    _, post = publish(client, token)

    response = client.post(
        f"/api/v1/posts/{post['id']}/signal", json={"kind": "works"}, headers=auth(token)
    )
    assert response.status_code == 422


def test_비로그인_신호는_거절(client):
    owner = register(client, "sg6@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "signalwriter6"}, headers=auth(owner))
    _, post = publish(client, owner)

    assert client.post(f"/api/v1/posts/{post['id']}/signal", json={"kind": "works"}).status_code == 401


def test_모르는_신호_종류는_거절(client):
    owner = register(client, "sg7@devshiplog.com")
    reader = register(client, "sg8@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "signalwriter7"}, headers=auth(owner))
    _, post = publish(client, owner)

    response = client.post(
        f"/api/v1/posts/{post['id']}/signal", json={"kind": "몰라요"}, headers=auth(reader)
    )
    assert response.status_code == 422


# ---------------------------------------------------------------- 탐색·대시보드


def test_스택으로_글을_찾는다(client):
    token = register(client, "br1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "browser1"}, headers=auth(token))
    publish(client, token, title="리액트 글", stacks=[{"name": "react", "version": "18.3"}])
    publish(client, token, title="고 글", stacks=[{"name": "go", "version": "1.23"}])

    titles = [i["title"] for i in client.get("/api/v1/public/stacks/react").json()["items"]]
    assert titles == ["리액트 글"]


def test_버전으로_좁힌다(client):
    token = register(client, "br2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "browser2"}, headers=auth(token))
    publish(client, token, title="18 글", stacks=[{"name": "react", "version": "18.3"}])
    publish(client, token, title="19 글", stacks=[{"name": "react", "version": "19.0"}])

    # 18 을 주면 18.x 를 모두 잡는다.
    titles = [i["title"] for i in
              client.get("/api/v1/public/stacks/react?version=18").json()["items"]]
    assert titles == ["18 글"]


def test_인기_스택_집계(client):
    token = register(client, "br3@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "browser3"}, headers=auth(token))
    publish(client, token, title="A", stacks=[{"name": "react", "version": "18"}])
    publish(client, token, title="B", stacks=[{"name": "react", "version": "19"}])
    publish(client, token, title="C", stacks=[{"name": "go", "version": "1"}])

    counts = {s["name"]: s["post_count"] for s in client.get("/api/v1/public/stacks").json()}
    assert counts["react"] == 2 and counts["go"] == 1


def test_갱신_목록은_안_되는_글을_먼저(client):
    """안 읽히는 낡은 글보다 읽히는데 안 되는 글이 급하다."""
    owner = register(client, "md1@devshiplog.com")
    reader = register(client, "md2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "maintainer"}, headers=auth(owner))

    _, old = publish(client, owner, title="낡은 글", stacks=[{"name": "react", "version": "17"}])
    _, broken = publish(client, owner, title="안 되는 글")
    client.post(f"/api/v1/posts/{broken['id']}/signal", json={"kind": "broken"}, headers=auth(reader))

    titles = [i["title"] for i in
              client.get("/api/v1/posts/needs-update", headers=auth(owner)).json()["items"]]
    assert titles[0] == "안 되는 글"
    assert "낡은 글" in titles


def test_검증된_글은_갱신_목록에_없다(client):
    token = register(client, "md3@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "maintainer3"}, headers=auth(token))
    _, post = publish(client, token, stacks=[{"name": "react", "version": "19"}])

    client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(token))
    assert client.get("/api/v1/posts/needs-update", headers=auth(token)).json()["items"] == []


def test_목록_카드에도_신선도가_실린다(client):
    """클릭한 뒤에야 낡은 글인 걸 알면 독자의 시간을 이미 쓴 뒤다."""
    token = register(client, "fd1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "feeder"}, headers=auth(token))
    publish(client, token, stacks=[{"name": "react", "version": "17"}])

    item = client.get("/api/v1/public/feed?limit=1").json()["items"][0]
    assert item["freshness"]["level"] in ("stale", "aging", "unverified")
    assert item["stacks"][0]["name"] == "react"
