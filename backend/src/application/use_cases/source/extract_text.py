from typing import Dict, Any
from ports.output.repositories.source_repository import SourceRepository
from infrastructure.database.models.source import SourceType


class ExtractTextUseCase:
    def __init__(self, source_repo: SourceRepository):
        self.source_repo = source_repo

    async def execute(self, user_id: str, raw_text: str) -> Dict[str, Any]:
        """텍스트에서 소스 추출"""
        source = await self.source_repo.create(
            user_id=user_id,
            source_type=SourceType.RAW,
            origin="raw_text",
            title="Text Input",
            content=raw_text,
        )

        return {
            "id": source.id,
            "type": source.type.value,
            "title": source.title,
            "status": "succeeded",
        }

