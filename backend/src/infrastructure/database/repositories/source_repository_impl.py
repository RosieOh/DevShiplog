from typing import List
from sqlalchemy.orm import Session
from infrastructure.database.models.source import Source, SourceType
from ports.output.repositories.source_repository import SourceRepository
import uuid


class SourceRepositoryImpl(SourceRepository):
    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        user_id: str,
        source_type: SourceType,
        origin: str,
        title: str,
        content: str,
        extracted_json: dict = None,
    ) -> Source:
        source = Source(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=source_type,
            origin=origin,
            title=title,
            content=content,
            extracted_json=extracted_json or {},
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    async def get_by_id(self, source_id: str) -> Source:
        return self.db.query(Source).filter(Source.id == source_id).first()

    async def get_by_ids(self, source_ids: List[str]) -> List[Source]:
        return self.db.query(Source).filter(Source.id.in_(source_ids)).all()

