"""요청 단위 문맥.

로그 한 줄만 보고는 "어느 요청에서 난 일인가" 를 알 수 없다.
동시 요청이 섞이면 스택트레이스와 그 앞뒤 로그를 이어 붙일 방법이 사라진다.

ContextVar 를 쓰는 이유: FastAPI 는 요청마다 태스크가 다르고,
ContextVar 는 태스크 경계를 따라간다. 전역 변수로 하면 요청끼리 값이 섞인다.
"""

from contextvars import ContextVar
from typing import Optional

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def current_request_id() -> Optional[str]:
    return request_id_var.get()


def current_user_id() -> Optional[str]:
    return user_id_var.get()
