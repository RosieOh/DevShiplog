from abc import ABC, abstractmethod
from typing import Dict, Any, List


class CrawlerService(ABC):
    @abstractmethod
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """URL에서 본문 추출"""
        pass

    @abstractmethod
    async def extract_from_rss(self, blog_url: str, sample_count: int = 5) -> List[Dict[str, Any]]:
        """RSS 피드에서 글 목록 추출"""
        pass

    @abstractmethod
    async def extract_from_blog(self, blog_url: str, sample_count: int = 5) -> List[str]:
        """블로그에서 샘플 글 추출"""
        pass

