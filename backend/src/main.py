import logging

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.application.errors import ApplicationError
from src.infrastructure.config.settings import settings
from src.ports.input.api.v1.router import api_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
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
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """예상치 못한 예외에서 스택트레이스가 클라이언트로 새어나가지 않도록 한다."""
    logger.exception("처리되지 않은 오류: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500, content={"detail": "서버 오류가 발생했습니다."}
    )


app.include_router(api_router, prefix="/api/v1")

# 업로드된 이미지 서빙.
# 운영에서는 S3/CDN 이 맡아야 한다. 앱 서버가 정적 파일을 나르면 확장이 막힌다.
_upload_root = Path(settings.UPLOAD_DIR)
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
