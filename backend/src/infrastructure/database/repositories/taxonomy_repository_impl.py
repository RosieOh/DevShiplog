import uuid
from typing import List, Optional, Sequence

from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from src.domain.services.identity import normalize_tag
from src.infrastructure.database.models.post import Post
from src.infrastructure.database.models.series import Series, SeriesPost
from src.infrastructure.database.models.tag import PostTag, Tag
from src.infrastructure.database.models.user import User
from src.ports.output.repositories.taxonomy_repository import SeriesRepository, TagRepository

MAX_TAGS_PER_POST = 10


def _decrement(column):
    return case((column > 0, column - 1), else_=0)


class TagRepositoryImpl(TagRepository):
    def __init__(self, db: Session):
        self.db = db

    def set_for_post(self, post_id: str, tag_names: Sequence[str]) -> List[Tag]:
        """태그를 통째로 교체한다. 사라진 태그의 카운터도 함께 줄인다."""
        wanted: List[tuple] = []
        seen = set()
        for raw in tag_names:
            name = normalize_tag(raw)
            if not name or name in seen:
                continue
            seen.add(name)
            wanted.append((name, raw.strip()[:40]))
            if len(wanted) >= MAX_TAGS_PER_POST:
                break

        current = {pt.tag.name: pt for pt in self._links(post_id)}

        # 빠진 태그 제거
        for name, link in current.items():
            if name not in seen:
                self.db.query(Tag).filter(Tag.id == link.tag_id).update(
                    {Tag.post_count: _decrement(Tag.post_count)}, synchronize_session=False
                )
                self.db.delete(link)

        tags: List[Tag] = []
        for name, display in wanted:
            tag = self.get_by_name(name)
            if tag is None:
                tag = Tag(
                    id=str(uuid.uuid4()), name=name, display_name=display or name, post_count=0
                )
                self.db.add(tag)
                self.db.flush()
            tags.append(tag)

            if name not in current:
                self.db.add(PostTag(post_id=post_id, tag_id=tag.id))
                self.db.query(Tag).filter(Tag.id == tag.id).update(
                    {Tag.post_count: Tag.post_count + 1}, synchronize_session=False
                )

        self.db.commit()
        return tags

    def _links(self, post_id: str) -> List[PostTag]:
        return (
            self.db.query(PostTag)
            .options(joinedload(PostTag.tag))
            .filter(PostTag.post_id == post_id)
            .all()
        )

    def list_for_post(self, post_id: str) -> List[Tag]:
        return [link.tag for link in self._links(post_id)]

    def get_by_name(self, name: str) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.name == normalize_tag(name)).first()

    def list_popular(self, limit: int) -> List[Tag]:
        return (
            self.db.query(Tag)
            .filter(Tag.post_count > 0)
            .order_by(Tag.post_count.desc(), Tag.name.asc())
            .limit(limit)
            .all()
        )

    def clear_for_post(self, post_id: str) -> None:
        for link in self._links(post_id):
            self.db.query(Tag).filter(Tag.id == link.tag_id).update(
                {Tag.post_count: _decrement(Tag.post_count)}, synchronize_session=False
            )
            self.db.delete(link)
        self.db.commit()


class SeriesRepositoryImpl(SeriesRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, slug: str, name: str, description: str = "") -> Series:
        series = Series(
            id=str(uuid.uuid4()),
            user_id=user_id,
            slug=slug,
            name=name[:200],
            description=description,
        )
        self.db.add(series)
        self.db.commit()
        self.db.refresh(series)
        return series

    def get_by_id(self, series_id: str) -> Optional[Series]:
        return self.db.query(Series).filter(Series.id == series_id).first()

    def get_public(self, handle: str, slug: str) -> Optional[Series]:
        return (
            self.db.query(Series)
            .join(User, Series.user_id == User.id)
            .filter(User.handle == handle.lower(), Series.slug == slug)
            .first()
        )

    def list_by_user(self, user_id: str) -> List[Series]:
        return (
            self.db.query(Series)
            .filter(Series.user_id == user_id)
            .order_by(Series.created_at.desc())
            .all()
        )

    def slugs_for_user(self, user_id: str) -> List[str]:
        return [r[0] for r in self.db.query(Series.slug).filter(Series.user_id == user_id).all()]

    def add_post(self, series_id: str, post_id: str) -> None:
        existing = (
            self.db.query(SeriesPost)
            .filter(SeriesPost.series_id == series_id, SeriesPost.post_id == post_id)
            .first()
        )
        if existing:
            return
        next_pos = (
            self.db.query(func.coalesce(func.max(SeriesPost.position), -1))
            .filter(SeriesPost.series_id == series_id)
            .scalar()
        ) + 1
        self.db.add(SeriesPost(series_id=series_id, post_id=post_id, position=next_pos))
        self.db.commit()

    def remove_post(self, series_id: str, post_id: str) -> None:
        self.db.query(SeriesPost).filter(
            SeriesPost.series_id == series_id, SeriesPost.post_id == post_id
        ).delete(synchronize_session=False)
        self.db.commit()
