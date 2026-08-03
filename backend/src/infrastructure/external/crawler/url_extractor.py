import logging
from typing import Any, Dict
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from readability import Document

from src.infrastructure.config.settings import settings
from src.infrastructure.external.crawler.net_guard import UnsafeURLError, safe_get, validate_url

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; DevshiplogBot/0.1; +https://devshiplog.example)"


class ExtractionError(Exception):
    """본문 추출 실패. 호출자가 사용자에게 노출할 메시지를 담는다."""


class URLExtractor:
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """URL에서 본문을 추출한다. 실패하면 ExtractionError 를 던진다."""
        html = await self.fetch_html(url)
        return self.parse_html(html, url)

    async def fetch_html(self, url: str) -> str:
        try:
            validate_url(url)
        except UnsafeURLError as exc:
            raise ExtractionError(str(exc)) from exc

        try:
            async with httpx.AsyncClient(
                timeout=settings.CRAWLER_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = await safe_get(client, url)
                response.raise_for_status()
                return response.text
        except UnsafeURLError as exc:
            raise ExtractionError(str(exc)) from exc
        except httpx.HTTPStatusError as exc:
            raise ExtractionError(
                f"페이지를 가져오지 못했습니다 (HTTP {exc.response.status_code})"
            ) from exc
        except httpx.HTTPError as exc:
            raise ExtractionError(f"페이지를 가져오지 못했습니다: {exc}") from exc

    def parse_html(self, html: str, base_url: str) -> Dict[str, Any]:
        try:
            doc = Document(html)
            title = doc.title()
            summary_html = doc.summary()
        except Exception as exc:  # readability 는 다양한 예외를 던진다
            raise ExtractionError(f"본문을 해석하지 못했습니다: {exc}") from exc

        soup = BeautifulSoup(summary_html, "html.parser")

        headings = [
            {"level": int(tag.name[1]), "text": tag.get_text().strip()}
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            if tag.get_text().strip()
        ]

        code_blocks = []
        for code in soup.find_all("pre"):
            text = code.get_text().strip()
            if len(text) > 10:
                code_blocks.append(text)

        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            else:
                src = urljoin(base_url, src)
            images.append(src)

        text_content = soup.get_text(separator="\n", strip=True)
        if not text_content.strip():
            raise ExtractionError("본문이 비어 있습니다 (로그인이 필요한 페이지일 수 있습니다)")

        return {
            "title": (title or base_url).strip(),
            "content": text_content,
            "headings": headings,
            "codeBlocks": code_blocks[:10],
            "images": images[:10],
        }
