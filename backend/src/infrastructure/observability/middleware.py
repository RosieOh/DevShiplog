"""요청 문맥과 접근 로그.

접근 로그를 직접 쓰는 이유: uvicorn 의 기본 접근 로그에는 소요 시간이 없다.
"느리다" 는 신고를 받았을 때 확인할 수 있는 게 없으면 추측만 하게 된다.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.infrastructure.observability.context import request_id_var, user_id_var

logger = logging.getLogger("access")

# 여기에 로그를 남기면 헬스체크가 1초에 한 번씩 로그를 채운다.
_QUIET_PATHS = frozenset({"/health", "/health/ready", "/"})


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 앞단(로드밸런서/프록시)이 이미 ID 를 붙였으면 그걸 쓴다.
        # 새로 만들면 프록시 로그와 앱 로그를 이을 수 없다.
        incoming = request.headers.get("x-request-id")
        request_id = incoming if incoming and len(incoming) <= 64 else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        user_token = user_id_var.set(None)
        # ContextVar 와 별개로 요청 객체에도 심는다.
        # 처리되지 않은 예외를 받는 핸들러(ServerErrorMiddleware)는 이 미들웨어 **바깥**에서
        # 돌기 때문에, 그 시점엔 ContextVar 가 이미 원래 값으로 되돌아가 있다.
        # 즉 정작 500 이 났을 때 요청 ID 를 잃는다 — 가장 필요한 순간에.
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # 여기서 잡지 않으면 소요 시간과 요청 ID 없이 스택트레이스만 남는다.
            # 다시 올려 보내서 예외 핸들러가 응답을 만들게 한다.
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.error(
                "%s %s 실패",
                request.method,
                request.url.path,
                extra={
                    "http_method": request.method,
                    "path": request.url.path,
                    "duration_ms": elapsed_ms,
                    "status": 500,
                },
            )
            raise
        finally:
            request_id_var.reset(token)
            user_id_var.reset(user_token)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers["X-Request-ID"] = request_id

        if request.url.path not in _QUIET_PATHS:
            # 5xx 는 error, 4xx 는 warning. 레벨로 거를 수 없으면 로그가 있어도 못 찾는다.
            level = (
                logging.ERROR
                if response.status_code >= 500
                else logging.WARNING
                if response.status_code >= 400
                else logging.INFO
            )
            logger.log(
                level,
                "%s %s %s (%sms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                extra={
                    "http_method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": elapsed_ms,
                },
            )
        return response
