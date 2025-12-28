from typing import Optional, List
from sqlalchemy.orm import Session
from infrastructure.database.models.style_profile import StyleProfile, StyleProfileStatus
from ports.output.repositories.style_profile_repository import StyleProfileRepository
import uuid


class StyleProfileRepositoryImpl(StyleProfileRepository):
    def __init__(self, db: Session):
        self.db = db

    async def create(self, user_id: str, blog_url: str, sample_count: int = 5) -> StyleProfile:
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

    async def get_by_id(self, profile_id: str) -> Optional[StyleProfile]:
        return self.db.query(StyleProfile).filter(StyleProfile.id == profile_id).first()

    async def get_by_user_id(self, user_id: str) -> List[StyleProfile]:
        return self.db.query(StyleProfile).filter(StyleProfile.user_id == user_id).all()

    async def update(self, profile: StyleProfile) -> StyleProfile:
        self.db.commit()
        self.db.refresh(profile)
        return profile

