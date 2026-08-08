import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.application.errors import ApplicationError, StaleDraftError
from src.infrastructure.config.settings import settings
from src.infrastructure.observability.context import current_request_id, request_id_var
from src.infrastructure.observability.errors import error_tracker, init_error_tracking
from src.infrastructure.observability.health import readiness
from src.infrastructure.observability.logging_setup import configure_logging
from src.infrastructure.observability.middleware import RequestContextMiddleware
from src.ports.input.api.v1.router import api_router

# 배포에서는 JSON, 개발에서는 사람이 읽는 형식.
# 개발자에게 JSON 을 읽히면 로그를 안 보게 되고, 안 보는 로그는 없는 것과 같다.
configure_logging(json_output=settings.LOG_JSON, debug=settings.DEBUG)
init_error_tracking(settings.SENTRY_DSN, settings.ENVIRONMENT, settings.APP_VERSION)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    """기동 시 오브젝트 저장소 버킷을 준비한다.

    MinIO 는 빈 상태로 뜬다. 여기서 만들어 두면 개발자가 콘솔에 들어가 손으로
    버킷을 만들 필요가 없고 CI 도 그냥 돈다.

    실패해도 기동은 막지 않는다. 저장소가 잠깐 늦게 뜨는 경우가 흔하고,
    그것 때문에 API 전체가 죽으면 업로드와 무관한 기능까지 못 쓴다.
    """
    if settings.STORAGE_BACKEND == "s3":
        try:
            from src.infrastructure.external.storage import get_storage

            get_storage().ensure_bucket()
        except Exception:
            logger.warning(
                "오브젝트 저장소 준비 실패 — 업로드가 동작하지 않을 수 있습니다", exc_info=True
            )
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Devshiplog API",
    description="기술 글 초안 생성 플랫폼 API",
    version="0.1.0",
    # 프로덕션에서는 스키마 문서를 노출하지 않는다.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# CORS 보다 뒤에 등록한다 — Starlette 는 나중에 등록한 미들웨어가 바깥에 놓이므로,
# 이 순서라야 CORS 프리플라이트까지 요청 ID 를 달고 로그에 남는다.
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError):
    """use case 예외를 HTTP 응답으로 변환한다."""
    body = {"detail": exc.message}
    if isinstance(exc, StaleDraftError):
        # 충돌은 "실패했다" 로 끝내면 안 된다. 클라이언트가 상대 내용을 보여주고
        # 덮어쓸지 고르게 하려면 현재 상태를 함께 줘야 한다.
        body["current_revision"] = exc.current_revision
        body["current_content_md"] = exc.content_md
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """예상치 못한 예외에서 스택트레이스가 클라이언트로 새어나가지 않도록 한다.

    로그만 남기면 아무도 안 본다. 여기서 수집기에도 넣어야 운영자 화면에 뜬다.
    응답에 지문을 실어 주는 이유: 사용자가 "오류가 났어요" 라고만 말하면
    로그에서 그 요청을 찾을 방법이 없다.
    """
    # 미들웨어가 심어 둔 값을 먼저 본다 — 여기는 미들웨어 바깥이라 ContextVar 는 비어 있다.
    request_id = getattr(request.state, "request_id", None) or current_request_id()
    fingerprint = error_tracker.capture(
        exc, path=request.url.path, method=request.method, request_id=request_id
    )
    # 로그 줄에도 요청 ID 가 붙어야 앞뒤 로그와 이어진다. 위와 같은 이유로 직접 넣는다.
    token = request_id_var.set(request_id)
    try:
        logger.exception(
            "처리되지 않은 오류: %s %s",
            request.method,
            request.url.path,
            extra={"fingerprint": fingerprint},
        )
    finally:
        request_id_var.reset(token)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "서버 오류가 발생했습니다.",
            "request_id": request_id,
            "error_id": fingerprint,
        },
    )


app.include_router(api_router, prefix="/api/v1")

# 업로드된 이미지 서빙 (로컬 디스크).
#
# 새 업로드는 오브젝트 저장소로 가지만, 이 마운트는 계속 유지한다.
# 저장소를 local → s3 로 바꾸기 전에 올라간 파일들의 주소가 DB(글 본문·커버·아바타)에
# 그대로 남아 있기 때문이다. 여기서 끊으면 과거 글의 이미지가 전부 깨진다.
# 디스크에 아무것도 없으면 마운트할 이유도 없다.
_upload_root = Path(settings.UPLOAD_DIR)
if settings.STORAGE_BACKEND == "local" or _upload_root.is_dir():
    _upload_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.UPLOAD_PUBLIC_PREFIX,
        StaticFiles(directory=_upload_root),
        name="uploads",
    )


@app.get("/")
def root():
    return {"message": "Devshiplog API", "version": "0.1.0"}


@app.get("/health")
def health():
    """살아있는가. 재시작 판단용이라 아무것도 두드리지 않는다."""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/health/ready")
def health_ready():
    """요청을 처리할 수 있는가. 트래픽 투입 판단용.

    준비되지 않았으면 503 을 낸다. 200 으로 답하면 로드밸런서가
    DB 가 끊긴 인스턴스로 트래픽을 계속 보낸다.
    """
    result = readiness()
    return JSONResponse(status_code=200 if result["ready"] else 503, content=result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
