from infrastructure.queue.celery_app import celery_app
from infrastructure.database.session import SessionLocal
from infrastructure.database.models.style_profile import StyleProfileStatus
from infrastructure.database.repositories.style_profile_repository_impl import StyleProfileRepositoryImpl
from infrastructure.external.crawler.crawler_service_impl import CrawlerServiceImpl
from infrastructure.external.llm.openai_client import OpenAIService


@celery_app.task
def analyze_style_profile_task(profile_id: str):
    """Style DNA 분석 Task"""
    db = SessionLocal()
    try:
        style_profile_repo = StyleProfileRepositoryImpl(db)
        crawler_service = CrawlerServiceImpl()
        llm_service = OpenAIService()

        # Profile 조회
        profile = style_profile_repo.get_by_id(profile_id)
        if not profile:
            return

        # 상태 업데이트
        profile.status = StyleProfileStatus.RUNNING
        db.commit()

        try:
            import asyncio
            # 블로그에서 샘플 글 추출
            blog_posts = asyncio.run(crawler_service.extract_from_blog(profile.blog_url, profile.sample_count))
            
            if not blog_posts:
                # RSS 시도
                rss_posts = asyncio.run(crawler_service.extract_from_rss(profile.blog_url, profile.sample_count))
                blog_posts = [post.get("content", "") for post in rss_posts if post.get("content")]

            if blog_posts:
                # LLM으로 스타일 분석
                style_analysis = asyncio.run(llm_service.analyze_style(blog_posts))
                
                # Profile 업데이트
                profile.profile_json = style_analysis
                profile.status = StyleProfileStatus.SUCCEEDED
            else:
                profile.status = StyleProfileStatus.FAILED
                profile.profile_json = {"error": "블로그 글을 추출할 수 없습니다."}

        except Exception as e:
            profile.status = StyleProfileStatus.FAILED
            profile.profile_json = {"error": str(e)}

        db.commit()
    finally:
        db.close()

