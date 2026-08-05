from fastapi import APIRouter

from src.ports.input.api.v1 import (
    analytics,
    auth,
    drafts,
    export,
    jobs,
    posts,
    profile,
    public,
    safety,
    schedules,
    series,
    social,
    sources,
    style_profiles,
    templates,
    uploads,
    usage,
)

api_router = APIRouter()

# --- 공개 (인증 없음) ------------------------------------------------------
# 독자와 검색 크롤러가 오는 경로. 절대 인증을 요구하지 않는다.
api_router.include_router(public.router, prefix="/public", tags=["public"])

# --- 계정 / 블로그 신원 ----------------------------------------------------
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])

# --- 글쓰기 도구 -----------------------------------------------------------
api_router.include_router(style_profiles.router, prefix="/style-profiles", tags=["style-profiles"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(safety.router, prefix="/safety", tags=["safety"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])

# --- 블로그 플랫폼 ---------------------------------------------------------
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(series.router, prefix="/series", tags=["series"])

# --- 작성 보조 -------------------------------------------------------------
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
