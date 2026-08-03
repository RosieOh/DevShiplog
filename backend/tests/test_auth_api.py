def test_register_returns_token(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "a@devshiplog.com", "password": "password1234", "name": "A"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "a@devshiplog.com"


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@devshiplog.com", "password": "password1234", "name": "A"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@devshiplog.com", "password": "1234", "name": "A"},
    )
    assert response.status_code == 422


def test_login_succeeds_with_correct_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@devshiplog.com", "password": "password1234", "name": "A"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@devshiplog.com", "password": "password1234"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_is_case_insensitive_on_email(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "Case@devshiplog.com", "password": "password1234", "name": "A"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "CASE@devshiplog.com", "password": "password1234"},
    )
    assert response.status_code == 200


def test_login_fails_with_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@devshiplog.com", "password": "password1234", "name": "A"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@devshiplog.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_does_not_reveal_whether_account_exists(client):
    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@devshiplog.com", "password": "password1234"},
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": "exists@devshiplog.com", "password": "password1234", "name": "A"},
    )
    bad_password = client.post(
        "/api/v1/auth/login",
        json={"email": "exists@devshiplog.com", "password": "nottherightone"},
    )
    assert missing.status_code == bad_password.status_code == 401
    assert missing.json()["detail"] == bad_password.json()["detail"]


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "tester@devshiplog.com"
