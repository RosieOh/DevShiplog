from typing import Optional, List
from sqlalchemy.orm import Session
from infrastructure.database.models.draft import Draft, DraftStatus
from infrastructure.database.models.draft_version import DraftVersion
from ports.output.repositories.draft_repository import DraftRepository
import uuid


class DraftRepositoryImpl(DraftRepository):
    def __init__(self, db: Session):
        self.db = db

    async def create(
        self,
        user_id: str,
        draft_type: str,
        audience: str,
        length_preset: str,
        style_profile_id: Optional[str] = None,
    ) -> Draft:
        draft = Draft(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=draft_type,
            audience=audience,
            length_preset=length_preset,
            style_profile_id=style_profile_id,
            status=DraftStatus.ACTIVE,
        )
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    async def get_by_id(self, draft_id: str) -> Optional[Draft]:
        return self.db.query(Draft).filter(Draft.id == draft_id).first()

    async def get_by_user_id(self, user_id: str) -> List[Draft]:
        return self.db.query(Draft).filter(Draft.user_id == user_id).order_by(Draft.created_at.desc()).all()

    async def create_version(
        self,
        draft_id: str,
        version_no: int,
        content_md: str,
        meta_json: dict = None,
    ) -> DraftVersion:
        version = DraftVersion(
            id=str(uuid.uuid4()),
            draft_id=draft_id,
            version_no=version_no,
            content_md=content_md,
            meta_json=meta_json or {},
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    async def get_latest_version(self, draft_id: str) -> Optional[DraftVersion]:
        return (
            self.db.query(DraftVersion)
            .filter(DraftVersion.draft_id == draft_id)
            .order_by(DraftVersion.version_no.desc())
            .first()
        )

    async def get_versions(self, draft_id: str) -> List[DraftVersion]:
        return (
            self.db.query(DraftVersion)
            .filter(DraftVersion.draft_id == draft_id)
            .order_by(DraftVersion.version_no.desc())
            .all()
        )

