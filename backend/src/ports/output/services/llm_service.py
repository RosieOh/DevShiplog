from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional


@dataclass
class LLMUsage:
    """LLM 호출 1회의 토큰/비용. UsageLog 기록과 쿼터 계산에 사용된다."""

    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    # 스트리밍 응답이 usage 를 돌려주지 않아 추정치를 쓴 경우 True
    estimated: bool = False


@dataclass
class LLMResult:
    """단발성 호출 결과 + 사용량"""

    value: Any
    usage: LLMUsage


class LLMStream:
    """비동기 청크 스트림. 소비가 끝나면 `usage` 가 채워진다.

    사용:
        stream = llm.generate_draft(...)
        async for chunk in stream:
            ...
        stream.usage  # 완료 후 사용 가능
    """

    def __init__(self, producer: Callable[["LLMStream"], AsyncIterator[str]]):
        self._producer = producer
        self.usage: Optional[LLMUsage] = None

    def __aiter__(self) -> AsyncIterator[str]:
        return self._producer(self)

    async def collect(self, on_chunk: Optional[Callable[[str], None]] = None) -> str:
        """스트림을 전부 모아 하나의 문자열로 반환한다."""
        parts: List[str] = []
        async for chunk in self:
            parts.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)
        return "".join(parts)


class LLMService(ABC):
    @abstractmethod
    async def generate_outline(
        self,
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> LLMResult:
        """목차 및 제목 후보 생성. value 는 dict"""
        ...

    @abstractmethod
    def generate_draft(
        self,
        outline: Dict[str, Any],
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> LLMStream:
        """본문 초안 생성 (스트리밍)"""
        ...

    @abstractmethod
    async def apply_style(
        self,
        draft_content: str,
        style_profile: Dict[str, Any],
    ) -> LLMResult:
        """Style DNA 적용 리라이트. value 는 str"""
        ...

    @abstractmethod
    def transform_draft(
        self,
        draft_content: str,
        transform_type: str,
    ) -> LLMStream:
        """Draft 변형 (짧게/길게/쉽게/깊게)"""
        ...

    @abstractmethod
    async def analyze_style(
        self,
        blog_posts: List[str],
    ) -> LLMResult:
        """블로그 글들로부터 스타일 분석. value 는 dict"""
        ...
