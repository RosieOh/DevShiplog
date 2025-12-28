from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any


class LLMService(ABC):
    @abstractmethod
    async def generate_outline(
        self,
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> Dict[str, Any]:
        """목차 및 제목 후보 생성"""
        pass

    @abstractmethod
    async def generate_draft(
        self,
        outline: Dict[str, Any],
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> AsyncIterator[str]:
        """본문 초안 생성 (스트리밍)"""
        pass

    @abstractmethod
    async def apply_style(
        self,
        draft_content: str,
        style_profile: Dict[str, Any],
    ) -> str:
        """Style DNA 적용 리라이트"""
        pass

    @abstractmethod
    async def transform_draft(
        self,
        draft_content: str,
        transform_type: str,
    ) -> AsyncIterator[str]:
        """Draft 변형 (짧게/길게/쉽게/깊게)"""
        pass

    @abstractmethod
    async def analyze_style(
        self,
        blog_posts: list[str],
    ) -> Dict[str, Any]:
        """블로그 글들로부터 스타일 분석"""
        pass

