import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from src.domain.enums import PostStatus
from src.infrastructure.database.models.post import Post
from src.infrastructure.database.models.tag import PostTag, Tag
from src.infrastructure.database.models.social import Follow
from src.infrastructure.database.models.user import User
from src.ports.output.repositories.post_repository import PostRepository

# 목록에서 태그와 작성자를 매번 개별 조회하면 N+1 이 된다.
_LIST_LOADS = (
    joinedload(Post.user),
    joinedload(Post.tags).joinedload(PostTag.tag),
)


class PostRepositoryImpl(PostRepository):
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------- 쓰기

    def create(
        self,
        user_id: str,
        draft_id: Optional[str],
        slug: str,
        title: str,
        content_md: str,
        summary: str,
        cover_url: Optional[str] = None,
    ) -> Post:
        post = Post(
            id=str(uuid.uuid4()),
            user_id=user_id,
            draft_id=draft_id,
            slug=slug,
            title=title[:300],
            content_md=content_md,
            summary=summary[:300],
            cover_url=cover_url,
            status=PostStatus.PUBLISHED,
            published_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    def update_content(
        self,
        post_id: str,
        title: str,
        content_md: str,
        summary: str,
        slug: Optional[str] = None,
        cover_url: Optional[str] = None,
    ) -> Post:
        post = self.get_by_id(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        post.title = title[:300]
        post.content_md = content_md
        post.summary = summary[:300]
        if slug is not None:
            post.slug = slug
        if cover_url is not None:
            post.cover_url = cover_url

        self.db.commit()
        self.db.refresh(post)
        return post

    def set_status(self, post_id: str, status: PostStatus) -> Post:
        post = self.get_by_id(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")
        post.status = status
        self.db.commit()
        self.db.refresh(post)
        return post

    def delete(self, post_id: str) -> None:
        post = self.get_by_id(post_id)
        if post:
            self.db.delete(post)
            self.db.commit()

    def increment_view(self, post_id: str) -> None:
        # 조회수는 정확성보다 비용이 중요하다. 원자적 UPDATE 로 락 경합을 피한다.
        self.db.query(Post).filter(Post.id == post_id).update(
            {Post.view_count: Post.view_count + 1}, synchronize_session=False
        )
        self.db.commit()

    # ------------------------------------------------------------- 읽기

    def get_by_id(self, post_id: str) -> Optional[Post]:
        return self.db.query(Post).filter(Post.id == post_id).first()

    def get_by_draft_id(self, draft_id: str) -> Optional[Post]:
        return self.db.query(Post).filter(Post.draft_id == draft_id).first()

    def get_public(self, handle: str, slug: str) -> Optional[Post]:
        return (
            self.db.query(Post)
            .options(*_LIST_LOADS)
            .join(User, Post.user_id == User.id)
            .filter(
                User.handle == handle.lower(),
                Post.slug == slug,
                Post.status == PostStatus.PUBLISHED,
            )
            .first()
        )

    def slugs_for_user(self, user_id: str) -> List[str]:
        return [
            row[0]
            for row in self.db.query(Post.slug).filter(Post.user_id == user_id).all()
        ]

    def list_by_user(
        self, user_id: str, only_published: bool, limit: int, offset: int
    ) -> List[Post]:
        q = self.db.query(Post).options(*_LIST_LOADS).filter(Post.user_id == user_id)
        if only_published:
            q = q.filter(Post.status == PostStatus.PUBLISHED)
        return q.order_by(Post.published_at.desc()).limit(limit).offset(offset).all()

    def count_by_user(self, user_id: str, only_published: bool) -> int:
        q = self.db.query(func.count(Post.id)).filter(Post.user_id == user_id)
        if only_published:
            q = q.filter(Post.status == PostStatus.PUBLISHED)
        return q.scalar() or 0

    def list_feed(
        self,
        limit: int,
        offset: int,
        sort: str = "recent",
        tag: Optional[str] = None,
        since_days: Optional[int] = None,
        exclude_user_ids: Sequence[str] = (),
    ) -> List[Post]:
        q = (
            self.db.query(Post)
            .options(*_LIST_LOADS)
            .filter(Post.status == PostStatus.PUBLISHED)
        )

        if tag:
            q = q.join(PostTag, PostTag.post_id == Post.id).join(
                Tag, Tag.id == PostTag.tag_id
            ).filter(Tag.name == tag.lower())

        if since_days:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=since_days)
            q = q.filter(Post.published_at >= cutoff)

        if exclude_user_ids:
            q = q.filter(~Post.user_id.in_(list(exclude_user_ids)))

        if sort == "trending":
            # 최근성과 반응을 함께 본다. 좋아요만 보면 오래된 글이 상단을 점유한다.
            q = q.order_by(
                (Post.like_count * 3 + Post.comment_count * 2).desc(),
                Post.published_at.desc(),
            )
        else:
            q = q.order_by(Post.published_at.desc())

        return q.limit(limit).offset(offset).all()

    def list_following_feed(self, user_id: str, limit: int, offset: int) -> List[Post]:
        following = select(Follow.following_id).where(Follow.follower_id == user_id)
        return (
            self.db.query(Post)
            .options(*_LIST_LOADS)
            .filter(Post.status == PostStatus.PUBLISHED, Post.user_id.in_(following))
            .order_by(Post.published_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def search(self, query: str, limit: int, offset: int) -> List[Post]:
        # MariaDB 전문검색 인덱스를 붙이기 전까지의 단순 구현.
        # LIKE '%...%' 는 인덱스를 못 타므로 글이 늘면 FULLTEXT 로 교체해야 한다.
        like = f"%{query.strip()}%"
        return (
            self.db.query(Post)
            .options(*_LIST_LOADS)
            .filter(
                Post.status == PostStatus.PUBLISHED,
                or_(Post.title.like(like), Post.summary.like(like)),
            )
            .order_by(Post.published_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def all_published_for_sitemap(self, limit: int = 50_000) -> List[Post]:
        return (
            self.db.query(Post)
            .options(joinedload(Post.user))
            .filter(Post.status == PostStatus.PUBLISHED)
            .order_by(Post.published_at.desc())
            .limit(limit)
            .all()
        )
