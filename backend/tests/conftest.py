import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 설정 로딩 전에 테스트용 환경변수를 박아둔다.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-not-production")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-not-a-real-key")

from src.infrastructure.database.session import Base, get_db  # noqa: E402
from src.main import app  # noqa: E402


@pytest.fixture()
def db_session():
    """테스트마다 새 인메모리 SQLite 를 쓴다.

    MariaDB 대신 SQLite 를 쓰므로 방언 차이가 있는 부분(예: JSON 함수)은
    이 스위트로 검증되지 않는다. 여기서는 라우팅/권한/도메인 로직을 검증한다.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """레이트리밋 카운터는 프로세스 전역이다.

    테스트끼리 IP 가 같아서(testclient) 앞 테스트가 쓴 횟수가 다음 테스트로 넘어간다.
    비우지 않으면 실패가 실행 순서에 따라 달라진다.
    """
    from src.infrastructure.ratelimit.limiter import rate_limiter

    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """가입 + 로그인해서 Authorization 헤더를 만든다."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "tester@devshiplog.com", "password": "password1234", "name": "테스터"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def other_auth_headers(client):
    """소유권 검사용 두 번째 사용자."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "intruder@devshiplog.com", "password": "password1234", "name": "침입자"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
