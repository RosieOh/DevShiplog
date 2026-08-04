import uuid
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.enums import DraftStatus
from src.infrastructure.database.models.draft import Draft
from src.infrastructure.database.models.draft_version import DraftVersion
from src.ports.output.repositories.draft_repository import DraftRepository


class DraftRepositoryImpl(DraftRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
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

    def get_by_id(self, draft_id: str) -> Optional[Draft]:
        return self.db.query(Draft).filter(Draft.id == draft_id).first()

    def get_by_user_id(self, user_id: str) -> List[Draft]:
        return (
            self.db.query(Draft)
            .filter(Draft.user_id == user_id)
            .order_by(Draft.created_at.desc())
            .all()
        )

    def create_version(
        self,
        draft_id: str,
        version_no: int,
        content_md: str,
        meta_json: Optional[dict] = None,
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

    def update_version_content(
        self,
        version_id: str,
        content_md: str,
        meta_json: Optional[dict] = None,
    ) -> DraftVersion:
        version = self.get_version_by_id(version_id)
        if not version:
            raise ValueError(f"DraftVersion {version_id} not found")

        version.content_md = content_md
        if meta_json is not None:
            version.meta_json = meta_json

        self.db.commit()
        self.db.refresh(version)
        return version

    def get_version_by_id(self, version_id: str) -> Optional[DraftVersion]:
        return self.db.query(DraftVersion).filter(DraftVersion.id == version_id).first()

    def get_latest_version(self, draft_id: str) -> Optional[DraftVersion]:
        return (
            self.db.query(DraftVersion)
            .filter(DraftVersion.draft_id == draft_id)
            .order_by(DraftVersion.version_no.desc())
            .first()
        )

    def get_versions(self, draft_id: str) -> List[DraftVersion]:
        return (
            self.db.query(DraftVersion)
            .filter(DraftVersion.draft_id == draft_id)
            .order_by(DraftVersion.version_no.desc())
            .all()
        )

    def next_version_no(self, draft_id: str) -> int:
        current_max = (
            self.db.query(func.max(DraftVersion.version_no))
            .filter(DraftVersion.draft_id == draft_id)
            .scalar()
        )
        return (current_max or 0) + 1
