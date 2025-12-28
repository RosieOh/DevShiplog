from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.config.settings import settings
from ports.input.api.v1.router import api_router

app = FastAPI(
    title="Devshiplog API",
    description="기술 글 초안 생성 플랫폼 API",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Devshiplog API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

