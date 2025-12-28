from typing import AsyncIterator, Dict, Any
import openai
from infrastructure.config.settings import settings
from ports.output.services.llm_service import LLMService


class OpenAIService(LLMService):
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_outline(
        self,
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> Dict[str, Any]:
        """목차 및 제목 후보 생성"""
        prompt = f"""다음 내용을 바탕으로 기술 블로그 글의 목차와 제목 후보를 생성해주세요.

글 타입: {draft_type}
대상 독자: {audience}
길이: {length_preset}

소스 내용:
{source_content[:3000]}

다음 JSON 형식으로 응답해주세요:
{{
  "titleCandidates": ["제목 후보 1", "제목 후보 2", "제목 후보 3", "제목 후보 4", "제목 후보 5"],
  "toc": [
    {{"heading": "서론", "level": 1}},
    {{"heading": "문제 정의", "level": 1}},
    {{"heading": "해결 방법", "level": 1}},
    {{"heading": "결론", "level": 1}}
  ],
  "keyPoints": ["핵심 포인트 1", "핵심 포인트 2"]
}}
"""

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 기술 블로그 글 기획 전문가입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        import json
        return json.loads(response.choices[0].message.content)

    async def generate_draft(
        self,
        outline: Dict[str, Any],
        source_content: str,
        draft_type: str,
        audience: str,
        length_preset: str,
    ) -> AsyncIterator[str]:
        """본문 초안 생성 (스트리밍)"""
        length_map = {
            "short": "800자 정도",
            "default": "1500~2500자",
            "long": "4000자 이상",
        }

        prompt = f"""다음 목차와 소스 내용을 바탕으로 기술 블로그 글 초안을 작성해주세요.

글 타입: {draft_type}
대상 독자: {audience}
길이: {length_map.get(length_preset, '1500~2500자')}

목차:
{outline.get('toc', [])}

소스 내용:
{source_content[:5000]}

마크다운 형식으로 작성해주세요. 코드 블록은 적절한 언어로 하이라이팅해주세요.
"""

        stream = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 기술 블로그 작가입니다. 명확하고 읽기 쉬운 글을 작성합니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def apply_style(
        self,
        draft_content: str,
        style_profile: Dict[str, Any],
    ) -> str:
        """Style DNA 적용 리라이트"""
        style_rules = style_profile.get("rules", {})
        tone = style_rules.get("tone", "담백")
        ending = style_rules.get("ending", "~합니다")

        prompt = f"""다음 글을 다음 스타일 규칙에 맞게 리라이트해주세요.

스타일 규칙:
- 톤: {tone}
- 종결어미: {ending}
- 구조 선호: {style_rules.get('structure', '문제-원인-해결-회고')}

원본 글:
{draft_content}

스타일에 맞게 자연스럽게 리라이트해주세요. 마크다운 형식은 유지해주세요.
"""

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 글쓰기 스타일 전문가입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        return response.choices[0].message.content

    async def transform_draft(
        self,
        draft_content: str,
        transform_type: str,
    ) -> AsyncIterator[str]:
        """Draft 변형 (짧게/길게/쉽게/깊게)"""
        transform_prompts = {
            "shorten": "이 글을 더 짧고 간결하게 요약해주세요. 핵심 내용만 남겨주세요.",
            "expand": "이 글을 더 자세하고 풍부하게 확장해주세요. 예시와 설명을 추가해주세요.",
            "simplify": "이 글을 초보자도 이해할 수 있도록 쉽게 풀어서 작성해주세요.",
            "deepen": "이 글을 더 깊이 있고 전문적으로 작성해주세요. 기술적 세부사항을 추가해주세요.",
            "style_stronger": "이 글의 스타일을 더 강하게 적용해주세요.",
        }

        prompt = f"""{transform_prompts.get(transform_type, "이 글을 개선해주세요.")}

원본 글:
{draft_content}

마크다운 형식은 유지해주세요.
"""

        stream = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 글쓰기 전문가입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def analyze_style(
        self,
        blog_posts: list[str],
    ) -> Dict[str, Any]:
        """블로그 글들로부터 스타일 분석"""
        combined_posts = "\n\n---\n\n".join(blog_posts[:5])

        prompt = f"""다음 블로그 글들을 분석하여 작성자의 스타일을 파악해주세요.

블로그 글들:
{combined_posts[:10000]}

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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 글쓰기 스타일 분석 전문가입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        import json
        return json.loads(response.choices[0].message.content)

