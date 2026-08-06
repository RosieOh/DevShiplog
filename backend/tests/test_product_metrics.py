"""제품 지표.

이 지표들이 "접을지 말지" 를 정하는 근거다. 계산이 틀리면 잘못된 판단을 하게 되므로
지표 자체를 검증한다.
"""

from datetime import datetime, timedelta, timezone

from src.application.use_cases.metrics import product_metrics as metrics


def register(client, email):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password1234", "name": "테스터"},
    ).json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


BODY = "본문입니다. " * 12


def publish(client, token, title="글", stacks=None):
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
        f"/api/v1/drafts/{draft['id']}/content", json={"content_md": BODY}, headers=auth(token)
    )
    payload = {"draft_id": draft["id"], "title": title}
    if stacks is not None:
        payload["stacks"] = stacks
    return client.post("/api/v1/posts", json=payload, headers=auth(token)).json()


# --------------------------------------------------------------- 기록


def test_발행하면_스택_확정_이벤트가_남는다(client, db_session):
    token = register(client, "pm1@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm1"}, headers=auth(token))
    publish(client, token)

    result = metrics.stack_correction_rate(db_session)
    assert result["publishes"] == 1


def test_작성자가_고치면_보정으로_기록된다(client, db_session):
    """보정률이 0% 면 추출이 완벽하거나 아무도 안 본 것이고, 둘은 전혀 다르다."""
    token = register(client, "pm2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm2"}, headers=auth(token))
    # 본문에 없는 스택을 직접 준다 = 보정
    publish(client, token, stacks=[{"name": "rust", "version": "1.83"}])

    assert metrics.stack_correction_rate(db_session)["corrected"] == 1


def test_스택_없이_발행하면_따로_센다(client, db_session):
    """이게 높으면 나머지 지표가 다 무의미하다."""
    token = register(client, "pm3@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm3"}, headers=auth(token))
    publish(client, token, stacks=[])

    assert metrics.stack_correction_rate(db_session)["published_empty"] == 1


def test_검증하면_이벤트가_남는다(client, db_session):
    token = register(client, "pm4@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm4"}, headers=auth(token))
    post = publish(client, token)

    client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(token))
    assert metrics.reverification_rate(db_session)["verified_posts"] == 1


def test_두_번_검증해야_재검증으로_센다(client, db_session):
    """첫 검증은 발행 직후의 의욕이고, 두 번째가 "다시 데려왔는가" 다."""
    token = register(client, "pm5@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm5"}, headers=auth(token))
    post = publish(client, token)

    client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(token))
    assert metrics.reverification_rate(db_session)["reverified_posts"] == 0

    client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(token))
    assert metrics.reverification_rate(db_session)["reverified_posts"] == 1


def test_신호에_반응하면_리드타임이_잡힌다(client, db_session):
    owner = register(client, "pm6@devshiplog.com")
    reader = register(client, "pm7@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm6"}, headers=auth(owner))
    post = publish(client, owner)

    client.post(f"/api/v1/posts/{post['id']}/signal", json={"kind": "broken"}, headers=auth(reader))
    before = metrics.signal_response(db_session)
    assert before["signaled_posts"] == 1 and before["responded"] == 0

    client.post(f"/api/v1/posts/{post['id']}/verify", headers=auth(owner))
    after = metrics.signal_response(db_session)
    assert after["responded"] == 1
    assert after["median_hours"] is not None


def test_잘_됐어요_는_반응_대상이_아니다(client, db_session):
    """반응률은 "안 된다는 신고에 움직였는가" 다."""
    owner = register(client, "pm8@devshiplog.com")
    reader = register(client, "pm9@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm8"}, headers=auth(owner))
    post = publish(client, owner)

    client.post(f"/api/v1/posts/{post['id']}/signal", json={"kind": "works"}, headers=auth(reader))
    assert metrics.signal_response(db_session)["signaled_posts"] == 0


# --------------------------------------------------------------- 알림


def test_안_됐어요_는_작성자에게_알린다(client):
    """알리지 않으면 작성자가 /maintain 에 들어갈 이유가 없고, 루프가 안 돈다."""
    owner = register(client, "nt1@devshiplog.com")
    reader = register(client, "nt2@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "nt1"}, headers=auth(owner))
    post = publish(client, owner)

    client.post(f"/api/v1/posts/{post['id']}/signal", json={"kind": "broken"}, headers=auth(reader))

    box = client.get("/api/v1/social/notifications", headers=auth(owner)).json()
    assert box["unread_count"] == 1
    assert box["items"][0]["type"] == "signal_broken"


def test_잘_됐어요_는_알리지_않는다(client):
    """좋은 소식으로 알림을 채우면 나쁜 소식이 묻힌다."""
    owner = register(client, "nt3@devshiplog.com")
    reader = register(client, "nt4@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "nt3"}, headers=auth(owner))
    post = publish(client, owner)

    client.post(f"/api/v1/posts/{post['id']}/signal", json={"kind": "works"}, headers=auth(reader))
    assert client.get("/api/v1/social/notifications", headers=auth(owner)).json()["unread_count"] == 0


# --------------------------------------------------------------- 판정


def test_표본이_적으면_판단을_보류한다(client, db_session):
    """20건도 안 되는데 "루프가 안 돈다" 고 결론내면 안 된다."""
    summary = metrics.summary(db_session)
    assert any("판단하기에 이릅니다" in v for v in summary["verdicts"])


def test_표본_진척을_알려준다(client, db_session):
    """"부족합니다" 만 띄우면 얼마나 남았는지 알 수 없고, 다시 볼 이유가 없다."""
    summary = metrics.summary(db_session)
    assert summary["sample"]["required"] == metrics.MIN_SAMPLE
    assert summary["sample"]["ready"] is False
    assert f"/{metrics.MIN_SAMPLE}건" in summary["verdicts"][0]


def test_지표가_비어_있어도_500_이_아니다(client):
    token = register(client, "pm10@devshiplog.com")
    response = client.get("/api/v1/posts/metrics/product", headers=auth(token))
    assert response.status_code == 200
    assert "verdicts" in response.json()


def test_계측_실패가_본_작업을_깨지_않는다(client, monkeypatch):
    """계측 때문에 발행이 실패하면 계측을 꺼버리게 된다."""
    from src.application.use_cases.metrics import product_metrics

    def boom(*args, **kwargs):
        raise RuntimeError("이벤트 테이블이 없다")

    monkeypatch.setattr(product_metrics.ProductEvent, "__init__", boom)

    token = register(client, "pm11@devshiplog.com")
    client.put("/api/v1/profile/me", json={"handle": "pm11"}, headers=auth(token))
    post = publish(client, token)
    assert post.get("id")
