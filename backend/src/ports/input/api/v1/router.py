from fastapi import APIRouter
from ports.input.api.v1 import auth, style_profiles, sources, drafts, jobs, safety, export, usage, templates, schedules, analytics

api_router = APIRouter()

# 라우터 등록
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(style_profiles.router, prefix="/style-profiles", tags=["style-profiles"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(safety.router, prefix="/safety", tags=["safety"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

