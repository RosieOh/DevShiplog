"""메일 발송.

Mailpit(개발용 SMTP 서버)이 떠 있으면 실제 발송까지 확인하고, 없으면 건너뛴다.
CI 에서는 서비스로 띄워 이 경로가 반드시 돌게 한다.
"""

import json
import os
import smtplib
import urllib.error
import urllib.request

import pytest

from src.infrastructure.config import settings as settings_module
from src.infrastructure.external import mail

MAILPIT_API = os.environ.get("MAILPIT_API", "http://localhost:8125")
SMTP_HOST = os.environ.get("MAILPIT_SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("MAILPIT_SMTP_PORT", "1125"))


def mailpit_up() -> bool:
    try:
        with urllib.request.urlopen(f"{MAILPIT_API}/api/v1/messages", timeout=3):
            return True
    except Exception:
        return False


requires_mailpit = pytest.mark.skipif(not mailpit_up(), reason="Mailpit 이 떠 있지 않습니다")


def clear_mailbox():
    request = urllib.request.Request(f"{MAILPIT_API}/api/v1/messages", method="DELETE")
    urllib.request.urlopen(request, timeout=5)


def mailbox():
    with urllib.request.urlopen(f"{MAILPIT_API}/api/v1/messages", timeout=5) as response:
        return json.load(response)


def body_of(message_id: str) -> str:
    with urllib.request.urlopen(f"{MAILPIT_API}/api/v1/message/{message_id}", timeout=5) as r:
        return json.load(r)["Text"]


@pytest.fixture
def smtp(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "SMTP_HOST", SMTP_HOST)
    monkeypatch.setattr(settings_module.settings, "SMTP_PORT", SMTP_PORT)
    monkeypatch.setattr(settings_module.settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings_module.settings, "SMTP_USER", "")
    monkeypatch.setattr(settings_module.settings, "MAIL_FROM", "no-reply@devshiplog.com")
    clear_mailbox()


# --------------------------------------------------------------- 설정 없음


def test_smtp_미설정이면_보내지_않고_False(monkeypatch):
    """개발에서 메일 서버 없이 전체 흐름을 돌려볼 수 있어야 한다."""
    monkeypatch.setattr(settings_module.settings, "SMTP_HOST", "")
    assert mail.send("someone@example.com", "제목", "본문") is False


def test_발송_실패가_예외로_새어나가지_않는다(monkeypatch):
    """메일이 안 갔다고 비밀번호 재설정 요청 자체가 500 이 되면 안 된다."""
    monkeypatch.setattr(settings_module.settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings_module.settings, "SMTP_PORT", 1)  # 아무도 없는 포트
    assert mail.send("someone@example.com", "제목", "본문") is False


# ------------------------------------------------------------- 실제 발송


@requires_mailpit
def test_실제로_메일이_도착한다(smtp):
    assert mail.send("reader@example.com", "제목입니다", "본문입니다") is True

    box = mailbox()
    assert box["messages_count"] == 1
    message = box["messages"][0]
    assert message["To"][0]["Address"] == "reader@example.com"
    assert message["From"]["Address"] == "no-reply@devshiplog.com"
    assert message["Subject"] == "제목입니다"


@requires_mailpit
def test_재설정_메일에_링크와_만료가_들어간다(smtp):
    url = "http://localhost:3000/auth/reset?token=abcdef123456"
    assert mail.send_password_reset("reader@example.com", url, 30) is True

    message = mailbox()["messages"][0]
    text = body_of(message["ID"])
    assert url in text
    assert "30분" in text
    # 본인이 요청하지 않았을 때 무엇을 해야 하는지 알려줘야 한다.
    assert "무시" in text


@requires_mailpit
def test_한글_제목이_깨지지_않는다(smtp):
    mail.send("reader@example.com", "한글 제목 테스트", "한글 본문입니다")
    message = mailbox()["messages"][0]
    assert message["Subject"] == "한글 제목 테스트"
    assert "한글 본문입니다" in body_of(message["ID"])


@requires_mailpit
def test_재설정_요청_API_가_실제로_메일을_보낸다(client, smtp, monkeypatch):
    """API → 백그라운드 태스크 → SMTP 까지 이어지는지."""
    monkeypatch.setattr(settings_module.settings, "FRONTEND_ORIGIN", "http://localhost:3000")

    email = "flow@devshiplog.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password1234", "name": "흐름"},
    )
    response = client.post("/api/v1/auth/password-reset", json={"email": email})
    assert response.status_code == 202

    box = mailbox()
    assert box["messages_count"] == 1
    text = body_of(box["messages"][0]["ID"])
    assert "http://localhost:3000/auth/reset?token=" in text


@requires_mailpit
def test_가입되지_않은_주소에는_메일이_가지_않는다(client, smtp):
    """응답은 같아야 하지만, 실제로 보내지는 않아야 한다."""
    response = client.post(
        "/api/v1/auth/password-reset", json={"email": "nobody-here@devshiplog.com"}
    )
    assert response.status_code == 202
    assert mailbox()["messages_count"] == 0
