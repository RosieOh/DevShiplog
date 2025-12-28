from typing import Dict, Any
import httpx
from readability import Document
from bs4 import BeautifulSoup
import re


class URLExtractor:
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """URL에서 본문 추출"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                response.raise_for_status()
                html = response.text
            except Exception as e:
                # Fallback: 단순 텍스트 추출
                return {
                    "title": url,
                    "content": f"URL 추출 실패: {str(e)}",
                    "headings": [],
                    "codeBlocks": [],
                    "images": [],
                }

        try:
            # Readability로 본문 추출
            doc = Document(html)
            title = doc.title()
            content = doc.summary()

            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(content, "html.parser")

            # 제목 추출
            headings = []
            for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                headings.append({
                    "level": int(heading.name[1]),
                    "text": heading.get_text().strip(),
                })

            # 코드 블록 추출
            code_blocks = []
            for code in soup.find_all(["pre", "code"]):
                code_text = code.get_text().strip()
                if code_text and len(code_text) > 10:  # 의미있는 코드만
                    code_blocks.append(code_text)

            # 이미지 추출
            images = []
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        # 상대 경로 처리
                        from urllib.parse import urljoin
                        src = urljoin(url, src)
                    images.append(src)

            # 텍스트 정리
            text_content = soup.get_text(separator="\n", strip=True)

            return {
                "title": title,
                "content": text_content,
                "headings": headings,
                "codeBlocks": code_blocks[:10],  # 최대 10개
                "images": images[:10],  # 최대 10개
            }
        except Exception as e:
            # Fallback
            return {
                "title": url,
                "content": f"본문 추출 실패: {str(e)}",
                "headings": [],
                "codeBlocks": [],
                "images": [],
            }

