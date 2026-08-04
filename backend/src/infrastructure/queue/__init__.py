"""작업 큐."""

import logging

from src.application.errors import ExternalServiceError

logger = logging.getLogger(__name__)


def enqueue(task, *args) -> None:
    """Celery 큐에 넣는다. 브로커가 죽어 있으면 502 로 바꿔 던진다.

    그냥 두면 kombu 예외가 그대로 올라가 500 이 되고, 사용자는 무엇을 다시
    해야 하는지 알 수 없다. 큐에 못 넣은 것은 사실이므로 숨기지 않되,
    재시도하면 되는 일이라는 것은 알려준다.
    """
    try:
        task.delay(*args)
    except Exception as exc:
        logger.warning("작업 큐 발행 실패: %s", task.name, exc_info=True)
        raise ExternalServiceError(
            "작업 대기열에 연결하지 못했습니다. 잠시 후 다시 시도해주세요."
        ) from exc
