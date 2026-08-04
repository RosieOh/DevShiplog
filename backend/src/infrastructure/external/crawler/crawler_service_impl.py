from typing import Dict, Any, List
from src.ports.output.services.crawler_service import CrawlerService
from src.infrastructure.external.crawler.url_extractor import URLExtractor
from src.infrastructure.external.crawler.blog_crawler import BlogCrawler


class CrawlerServiceImpl(CrawlerService):
    def __init__(self):
        self.url_extractor = URLExtractor()
        self.blog_crawler = BlogCrawler()

    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """URL에서 본문 추출"""
        return await self.url_extractor.extract_from_url(url)

    async def extract_from_rss(self, blog_url: str, sample_count: int = 5) -> List[Dict[str, Any]]:
        """RSS 피드에서 글 목록 추출"""
        return await self.blog_crawler.extract_from_rss(blog_url, sample_count)

    async def extract_from_blog(self, blog_url: str, sample_count: int = 5) -> List[str]:
        """블로그에서 샘플 글 추출"""
        return await self.blog_crawler.extract_from_blog(blog_url, sample_count)

