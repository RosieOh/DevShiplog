import logging
from typing import Any, Dict, List
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup

from src.infrastructure.config.settings import settings
from src.infrastructure.external.crawler.net_guard import UnsafeURLError, safe_get
from src.infrastructure.external.crawler.url_extractor import (
    USER_AGENT,
    ExtractionError,
    URLExtractor,
)

logger = logging.getLogger(__name__)

# RSS/Atom 을 못 찾았을 때 시도해 볼 관례적인 경로
FALLBACK_FEED_PATHS = ("/rss", "/feed", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml")


class BlogCrawler:
    def __init__(self):
        self.url_extractor = URLExtractor()

    async def _discover_feed_urls(self, client: httpx.AsyncClient, blog_url: str) -> List[str]:
        """HTML 의 <link rel="alternate"> 로 피드를 찾고, 없으면 관례 경로를 쓴다."""
        discovered: List[str] = []
        try:
            response = await safe_get(client, blog_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("link", rel=lambda v: v and "alternate" in v):
                href = link.get("href")
                link_type = (link.get("type") or "").lower()
                if href and ("rss" in link_type or "atom" in link_type or "xml" in link_type):
                    discovered.append(urljoin(blog_url, href))
        except (httpx.HTTPError, UnsafeURLError) as exc:
            logger.info("피드 자동 탐색 실패 (%s): %s", blog_url, exc)

        base = blog_url.rstrip("/")
        discovered.extend(base + path for path in FALLBACK_FEED_PATHS)

        seen, ordered = set(), []
        for url in discovered:
            if url not in seen:
                seen.add(url)
                ordered.append(url)
        return ordered

    async def extract_from_rss(self, blog_url: str, sample_count: int = 5) -> List[Dict[str, Any]]:
        """RSS/Atom 피드에서 글 목록을 추출한다.

        feedparser 에 URL 을 직접 넘기면 SSRF 검사를 우회하고 이벤트 루프도 막으므로,
        반드시 safe_get 으로 받아온 바이트를 파싱한다.
        """
        async with httpx.AsyncClient(
            timeout=settings.CRAWLER_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            for feed_url in await self._discover_feed_urls(client, blog_url):
                try:
                    response = await safe_get(client, feed_url)
                    if response.status_code >= 400:
                        continue
                    feed = feedparser.parse(response.content)
                except (httpx.HTTPError, UnsafeURLError) as exc:
                    logger.debug("피드 요청 실패 (%s): %s", feed_url, exc)
                    continue

                if not feed.entries:
                    continue

                posts = []
                for entry in feed.entries[:sample_count]:
                    posts.append(
                        {
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "content": self._entry_text(entry),
                        }
                    )
                if posts:
                    return posts

        return []

    @staticmethod
    def _entry_text(entry: Any) -> str:
        """content > summary 순으로 본문 텍스트를 뽑고 HTML 태그를 제거한다."""
        raw = ""
        contents = entry.get("content")
        if contents:
            raw = contents[0].get("value", "") or ""
        if not raw:
            raw = entry.get("summary", "") or ""
        if not raw:
            return ""
        return BeautifulSoup(raw, "html.parser").get_text(separator="\n", strip=True)

    async def extract_from_blog(self, blog_url: str, sample_count: int = 5) -> List[str]:
        """블로그에서 스타일 분석용 샘플 글 본문들을 가져온다.

        1) 피드에 전문이 실려 있으면 그대로 사용
        2) 요약만 있으면 각 글 URL 을 실제로 열어 본문을 추출
        """
        posts = await self.extract_from_rss(blog_url, sample_count)

        samples: List[str] = []
        for post in posts:
            content = post.get("content", "")
            # 요약만 실린 피드는 본문이 짧다. 이럴 때는 원문을 직접 가져온다.
            if len(content) < 500 and post.get("url"):
                try:
                    extracted = await self.url_extractor.extract_from_url(post["url"])
                    content = extracted.get("content", content)
                except ExtractionError as exc:
                    logger.info("샘플 글 추출 실패 (%s): %s", post.get("url"), exc)
            if content.strip():
                samples.append(content)

        return samples[:sample_count]
