"""구조화 로그.

`%(asctime)s %(levelname)s ...` 는 사람이 읽기엔 좋지만 검색이 안 된다.
"어제 오후에 난 500 을 요청 ID 로 모아 봐라" 를 하려면 필드가 있어야 한다.

개발에서는 사람이 읽는 형식을, 배포에서는 JSON 을 쓴다.
개발자에게 JSON 을 읽히면 로그를 안 보게 되고, 안 보는 로그는 없는 것과 같다.
"""

import json
import logging
import sys
from typing import Any, Dict

from src.infrastructure.observability.context import current_request_id, current_user_id

# 로거가 기본으로 들고 있는 필드. 여기에 없는 것만 사용자 필드로 본다.
_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"asctime", "message", "taskName"}


class JsonFormatter(logging.Formatter):
    """한 줄에 하나의 JSON 객체."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        request_id = current_request_id()
        if request_id:
            payload["request_id"] = request_id
        user_id = current_user_id()
        if user_id:
            payload["user_id"] = user_id

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        # logger.info("...", extra={"path": ...}) 로 넘어온 값을 그대로 싣는다.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """개발용. 요청 ID 만 앞에 붙인다."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        request_id = current_request_id()
        return f"[{request_id[:8]}] {base}" if request_id else base


def configure_logging(*, json_output: bool, debug: bool) -> None:
    """루트 로거를 갈아끼운다.

    basicConfig 를 쓰지 않는다 — 이미 핸들러가 붙어 있으면 조용히 아무 일도 안 하기 때문에,
    uvicorn 처럼 먼저 로깅을 건드리는 실행 환경에서 설정이 통째로 무시된다.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if json_output
        else HumanFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # uvicorn 은 자기 로거에 핸들러를 따로 단다. 그대로 두면 접근 로그만
    # 형식이 달라져서, 정작 배포 환경에서 파싱이 반쪽이 된다.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
