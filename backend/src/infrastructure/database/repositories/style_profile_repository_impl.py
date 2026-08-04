import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.enums import StyleProfileStatus
from src.infrastructure.database.models.style_profile import StyleProfile
from src.ports.output.repositories.style_profile_repository import StyleProfileRepository


class StyleProfileRepositoryImpl(StyleProfileRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, blog_url: str, sample_count: int = 5) -> StyleProfile:
        profile = StyleProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            blog_url=blog_url,
            sample_count=sample_count,
            status=StyleProfileStatus.QUEUED,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_by_id(self, profile_id: str) -> Optional[StyleProfile]:
        return (
            self.db.query(StyleProfile)
            .populate_existing()
            .filter(StyleProfile.id == profile_id)
            .first()
        )

    def get_by_user_id(self, user_id: str) -> List[StyleProfile]:
        return (
            self.db.query(StyleProfile)
            .filter(StyleProfile.user_id == user_id)
            .order_by(StyleProfile.created_at.desc())
            .all()
        )

    def update_result(
        self,
        profile_id: str,
        status: StyleProfileStatus,
        profile_json: Optional[dict] = None,
        error_text: Optional[str] = None,
    ) -> StyleProfile:
        profile = self.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"StyleProfile {profile_id} not found")

        profile.status = status
        if profile_json is not None:
            profile.profile_json = profile_json
        profile.error_text = error_text

        self.db.commit()
        self.db.refresh(profile)
        return profile
