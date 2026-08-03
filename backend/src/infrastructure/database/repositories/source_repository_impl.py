import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.enums import SourceType
from src.infrastructure.database.models.source import Source
from src.ports.output.repositories.source_repository import SourceRepository


class SourceRepositoryImpl(SourceRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: str,
        source_type: SourceType,
        origin: str,
        title: str,
        content: str,
        extracted_json: Optional[dict] = None,
    ) -> Source:
        source = Source(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=source_type,
            origin=origin[:500],
            title=(title or "")[:500],
            content=content,
            extracted_json=extracted_json or {},
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_by_id(self, source_id: str) -> Optional[Source]:
        return self.db.query(Source).filter(Source.id == source_id).first()

    def get_by_ids(self, source_ids: List[str]) -> List[Source]:
        if not source_ids:
            return []
        return self.db.query(Source).filter(Source.id.in_(source_ids)).all()

    def get_owned_by_ids(self, user_id: str, source_ids: List[str]) -> List[Source]:
        if not source_ids:
            return []
        return (
            self.db.query(Source)
            .filter(Source.user_id == user_id, Source.id.in_(source_ids))
            .all()
        )
