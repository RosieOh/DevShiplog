from typing import Any, Dict

from src.application.errors import ValidationError
from src.domain.enums import SourceType
from src.ports.output.repositories.source_repository import SourceRepository

MAX_RAW_TEXT_CHARS = 200_000


class ExtractTextUseCase:
    def __init__(self, source_repo: SourceRepository):
        self.source_repo = source_repo

    def execute(self, user_id: str, raw_text: str) -> Dict[str, Any]:
        """붙여넣은 텍스트를 Source 로 저장한다."""
        text = (raw_text or "").strip()
        if not text:
            raise ValidationError("텍스트가 비어 있습니다.")
        if len(text) > MAX_RAW_TEXT_CHARS:
            raise ValidationError(
                f"텍스트가 너무 깁니다 (최대 {MAX_RAW_TEXT_CHARS:,}자)."
            )

        # 첫 줄을 제목으로 사용하면 대시보드에서 구분하기 쉽다.
        first_line = text.splitlines()[0].strip()
        title = (first_line[:80] or "Text Input") if first_line else "Text Input"

        source = self.source_repo.create(
            user_id=user_id,
            source_type=SourceType.RAW,
            origin="raw_text",
            title=title,
            content=text,
        )

        return {
            "id": source.id,
            "type": source.type.value,
            "title": source.title,
            "status": "succeeded",
            "error": None,
        }
