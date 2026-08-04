"""메일 발송.

SMTP_HOST 가 비어 있으면 실제로 보내지 않고 로그만 남긴다. 개발·테스트에서
메일 서버 없이 전체 흐름을 돌려볼 수 있어야 하기 때문이다.

발송 실패는 호출부로 던지지 않는다. 메일이 안 갔다고 회원가입이나 비밀번호
재설정 요청 자체를 500 으로 만들면, 사용자는 무엇을 다시 해야 할지 알 수 없다.
"""

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10.0


def send(to: str, subject: str, body: str) -> bool:
    """보냈으면 True. 설정이 없거나 실패하면 False."""
    if not settings.SMTP_HOST:
        logger.info("[메일 미발송 — SMTP 미설정] to=%s subject=%s\n%s", to, subject, body)
        return False

    message = EmailMessage()
    message["From"] = formataddr(("Devshiplog", settings.MAIL_FROM))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=TIMEOUT_SECONDS) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception:
        logger.warning("메일 발송 실패 to=%s subject=%s", to, subject, exc_info=True)
        return False


def send_password_reset(to: str, reset_url: str, ttl_minutes: int) -> bool:
    return send(
        to,
        "[Devshiplog] 비밀번호 재설정",
        f"""비밀번호를 재설정하려면 아래 주소로 접속해주세요.

{reset_url}

이 링크는 {ttl_minutes}분 뒤에 만료됩니다.
본인이 요청한 것이 아니라면 이 메일을 무시하셔도 됩니다. 비밀번호는 바뀌지 않습니다.
""",
    )
