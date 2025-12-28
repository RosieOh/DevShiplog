from typing import List, Dict, Any
import httpx
import feedparser
from infrastructure.external.crawler.url_extractor import URLExtractor


class BlogCrawler:
    def __init__(self):
        self.url_extractor = URLExtractor()

    async def extract_from_rss(self, blog_url: str, sample_count: int = 5) -> List[Dict[str, Any]]:
        """RSS 피드에서 글 목록 추출"""
        # RSS URL 추정
        rss_urls = [
            f"{blog_url.rstrip('/')}/rss",
            f"{blog_url.rstrip('/')}/feed",
            f"{blog_url.rstrip('/')}/atom.xml",
        ]

        for rss_url in rss_urls:
            try:
                feed = feedparser.parse(rss_url)
                if feed.entries:
                    posts = []
                    for entry in feed.entries[:sample_count]:
                        posts.append({
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "content": entry.get("content", [{}])[0].get("value", "") if entry.get("content") else "",
                        })
                    return posts
            except Exception:
                continue

        return []

    async def extract_from_blog(self, blog_url: str, sample_count: int = 5) -> List[str]:
        """블로그에서 샘플 글 추출"""
        # RSS 우선 시도
        rss_posts = await self.extract_from_rss(blog_url, sample_count)
        if rss_posts:
            return [post.get("content", "") for post in rss_posts if post.get("content")]

        # RSS 실패 시 공개 페이지 크롤링 (간단한 구현)
        # 실제로는 각 플랫폼별 API 사용 권장
        posts = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(blog_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                # 간단한 파싱 (실제로는 플랫폼별 맞춤 파싱 필요)
                # 여기서는 예시로 빈 리스트 반환
                pass
        except Exception:
            pass

        return posts

