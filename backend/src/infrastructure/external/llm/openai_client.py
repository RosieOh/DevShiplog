import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import openai

from src.infrastructure.config.settings import settings
from src.ports.output.services.llm_service import (
    LLMResult,
    LLMService,
    LLMStream,
    LLMUsage,
)

logger = logging.getLogger(__name__)

# 프롬프트에 실어 보내는 소스 길이 상한 (문자 수)
MAX_SOURCE_CHARS = 12_000
MAX_STYLE_SAMPLE_CHARS = 10_000

LENGTH_MAP = {
    "short": "800자 정도",
    "default": "1500~2500자",
    "long": "4000자 이상",
}

TRANSFORM_PROMPTS = {
    "shorten": "이 글을 더 짧고 간결하게 요약해주세요. 핵심 내용만 남겨주세요.",
    "expand": "이 글을 더 자세하고 풍부하게 확장해주세요. 예시와 설명을 추가해주세요.",
    "simplify": "이 글을 초보자도 이해할 수 있도록 쉽게 풀어서 작성해주세요.",
    "deepen": "이 글을 더 깊이 있고 전문적으로 작성해주세요. 기술적 세부사항을 추가해주세요.",
    "style_stronger": "이 글의 스타일을 더 강하게 적용해주세요.",
}


def _estimate_tokens(text: str) -> int:
    """usage 를 못 받았을 때 쓰는 러프한 추정치 (한글 혼용 기준 대략 문자수/2.5)."""
    return max(1, int(len(text) / 2.5))


class OpenAIService(LLMService):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        key = api_key if api_key is not None else settings.OPENAI_API_KEY
        if not key:
            raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다. backend/.env 를 확인하세요.")
        self.client = openai.AsyncOpenAI(api_key=key)
        self.model = model or settings.LLM_MODEL

    # ------------------------------------------------------------------ utils

    def _build_usage(self, prompt_tokens: int, completion_tokens: int, estimated: bool) -> LLMUsage:
        cost = (
            prompt_tokens / 1_000_000 * settings.LLM_INPUT_COST_PER_1M
            + completion_tokens / 1_000_000 * settings.LLM_OUTPUT_COST_PER_1M
        )
        return LLMUsage(
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            estimated=estimated,
        )

    def _usage_from_response(self, response: Any, fallback_text: str = "") -> LLMUsage:
        usage = getattr(response, "usage", None)
        if usage is not None:
            return self._build_usage(
                getattr(usage, "prompt_tokens", 0) or 0,
                getattr(usage, "completion_tokens", 0) or 0,
                estimated=False,
            )
        return self._build_usage(0, _estimate_tokens(fallback_text), estimated=True)

    @staticmethod
    def _parse_json(raw: str, context: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"{context}: LLM 이 올바른 JSON 을 반환하지 않았습니다 ({exc})") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{context}: JSON 객체가 아닙니다")
        return parsed

    async def _stream_chat(
        self,
        stream_obj: LLMStream,
        *,
        system: str,
        prompt: str,
        temperature: float,
    ) -> AsyncIterator[str]:
        """공통 스트리밍 루프. 완료 시 stream_obj.usage 를 채운다."""
        collected: List[str] = []
        usage_payload = None

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "stream": True,
        }
        # 최신 API 는 스트리밍에서도 usage 를 돌려준다. 구버전 SDK/게이트웨이에서는
        # 이 파라미터가 거부될 수 있으므로 그때는 파라미터 없이 재시도하고 추정치를 쓴다.
        try:
            stream = await self.client.chat.completions.create(
                **kwargs, stream_options={"include_usage": True}
            )
        except (TypeError, openai.BadRequestError):
            logger.warning("stream_options 미지원 — 토큰 사용량은 추정치로 기록됩니다")
            stream = await self.client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if getattr(chunk, "usage", None):
                usage_payload = chunk.usage
            if not chunk.choices:
                continue
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                collected.append(content)
                yield content

        if usage_payload is not None:
            stream_obj.usage = self._build_usage(
                getattr(usage_payload, "prompt_tokens", 0) or 0,
                getattr(usage_payload, "completion_tokens", 0) or 0,
                estimated=False,
            )
        else:
            stream_obj.usage = self._build_usage(
                _estimate_tokens(prompt), _estimate_tokens("".join(collected)), estimated=True
            )

    # ------------------------------------------------------------------- API

    async def generate_outline(
        self,
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> LLMResult:
        prompt = f"""다음 내용을 바탕으로 기술 블로그 글의 목차와 제목 후보를 생성해주세요.

글 타입: {draft_type}
대상 독자: {audience}
길이: {LENGTH_MAP.get(length_preset, LENGTH_MAP['default'])}

소스 내용:
{source_content[:MAX_SOURCE_CHARS]}

다음 JSON 형식으로 응답해주세요:
{{
  "titleCandidates": ["제목 후보 1", "제목 후보 2", "제목 후보 3"],
  "toc": [
    {{"heading": "서론", "level": 1}},
    {{"heading": "문제 정의", "level": 1}}
  ],
  "keyPoints": ["핵심 포인트 1", "핵심 포인트 2"]
}}
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "당신은 기술 블로그 글 기획 전문가입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return LLMResult(
            value=self._parse_json(content, "generate_outline"),
            usage=self._usage_from_response(response, content),
        )

    def generate_draft(
        self,
        outline: Dict[str, Any],
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> LLMStream:
        toc_text = "\n".join(
            f"{'#' * int(item.get('level', 1) or 1)} {item.get('heading', '')}"
            for item in outline.get("toc", [])
            if isinstance(item, dict)
        )
        prompt = f"""다음 목차와 소스 내용을 바탕으로 기술 블로그 글 초안을 작성해주세요.

글 타입: {draft_type}
대상 독자: {audience}
길이: {LENGTH_MAP.get(length_preset, LENGTH_MAP['default'])}

목차:
{toc_text}

소스 내용:
{source_content[:MAX_SOURCE_CHARS]}

마크다운 형식으로 작성해주세요. 코드 블록은 적절한 언어로 하이라이팅해주세요.
"""

        def producer(stream_obj: LLMStream) -> AsyncIterator[str]:
            return self._stream_chat(
                stream_obj,
                system="당신은 기술 블로그 작가입니다. 명확하고 읽기 쉬운 글을 작성합니다.",
                prompt=prompt,
                temperature=0.7,
            )

        return LLMStream(producer)

    async def apply_style(
        self,
        draft_content: str,
        style_profile: Dict[str, Any],
    ) -> LLMResult:
        rules = style_profile.get("rules", style_profile) or {}
        prompt = f"""다음 글을 아래 스타일 규칙에 맞게 리라이트해주세요.

스타일 규칙:
- 톤: {rules.get('tone', '담백')}
- 종결어미: {rules.get('ending', '~합니다')}
- 구조 선호: {rules.get('structure', '문제-원인-해결-회고')}

원본 글:
{draft_content}

스타일에 맞게 자연스럽게 리라이트해주세요. 마크다운 형식은 유지해주세요.
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "당신은 글쓰기 스타일 전문가입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )
        content = response.choices[0].message.content or ""
        return LLMResult(value=content, usage=self._usage_from_response(response, content))

    def transform_draft(self, draft_content: str, transform_type: str) -> LLMStream:
        instruction = TRANSFORM_PROMPTS.get(transform_type, "이 글을 개선해주세요.")
        prompt = f"""{instruction}

원본 글:
{draft_content}

마크다운 형식은 유지해주세요.
"""

        def producer(stream_obj: LLMStream) -> AsyncIterator[str]:
            return self._stream_chat(
                stream_obj,
                system="당신은 글쓰기 전문가입니다.",
                prompt=prompt,
                temperature=0.7,
            )

        return LLMStream(producer)

    async def analyze_style(self, blog_posts: List[str]) -> LLMResult:
        combined = "\n\n---\n\n".join(blog_posts[:5])[:MAX_STYLE_SAMPLE_CHARS]
        prompt = f"""다음 블로그 글들을 분석하여 작성자의 스타일을 파악해주세요.

블로그 글들:
{combined}

다음 JSON 형식으로 응답해주세요:
{{
  "tone": "담백|캐주얼|공식",
  "ending": "~합니다|~해요|~이다",
  "structure": "문제-원인-해결-회고|튜토리얼|릴리즈노트",
  "codeBlockFrequency": "낮음|중간|높음",
  "commonPhrases": ["자주 쓰는 표현 1", "자주 쓰는 표현 2"],
  "rules": {{
    "tone": "담백",
    "ending": "~합니다",
    "structure": "문제-원인-해결-회고",
    "codeBlockFrequency": "중간"
  }}
}}
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "당신은 글쓰기 스타일 분석 전문가입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return LLMResult(
            value=self._parse_json(content, "analyze_style"),
            usage=self._usage_from_response(response, content),
        )
