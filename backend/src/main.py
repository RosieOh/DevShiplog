import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.application.errors import ApplicationError, StaleDraftError
from src.infrastructure.config.settings import settings
from src.ports.input.api.v1.router import api_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
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
    """예상치 못한 예외에서 스택트레이스가 클라이언트로 새어나가지 않도록 한다."""
    logger.exception("처리되지 않은 오류: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500, content={"detail": "서버 오류가 발생했습니다."}
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
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
