import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlalchemy import case, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.domain.enums import PostStatus
from src.infrastructure.database.models.post import Post
from src.infrastructure.database.models.post_view import PostView
from src.infrastructure.database.models.tag import PostTag, Tag
from src.infrastructure.database.models.tech import PostStack
from src.infrastructure.database.models.social import Follow, PostLike
from src.infrastructure.database.models.user import User
from src.ports.output.repositories.post_repository import PostRepository

# BOOLEAN MODE 연산자로 해석되는 문자들. 사용자 입력에서 걷어내야 한다.
# 안 걷어내면 '-' 로 시작하는 검색어가 "이걸 제외하라" 로 읽혀 결과가 뒤집힌다.
_FT_OPERATORS = str.maketrans({c: " " for c in '+-<>~*()"@'})


def _boolean_mode_query(term: str) -> str:
    """검색어 → BOOLEAN MODE 표현식.

    각 토큰에 접두 와일드카드를 붙인다. 한국어는 '리액트를' 처럼 조사가 붙어 다녀서,
    정확히 일치하는 토큰만 찾으면 '리액트' 검색이 거의 안 걸린다.
    """
    # 2글자 미만은 버린다. docker-compose 에서 innodb_ft_min_token_size=2 로 맞춰 뒀으므로
    # 그보다 짧은 토큰은 애초에 색인에 없다 (보내 봐야 결과가 0이고 질의만 무거워진다).
    tokens = [t for t in term.translate(_FT_OPERATORS).split() if len(t) >= 2]
    return " ".join(f"+{t}*" for t in tokens[:8])  # 토큰이 너무 많으면 질의가 무거워진다


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

    def record_view(
        self, post_id: str, viewer_key: str, user_id: Optional[str] = None, window_hours: int = 24
    ) -> bool:
        """조회를 기록한다. 이번이 처음(또는 기간이 지난 재방문)이면 True.

        True 일 때만 조회수를 올린다. 그러지 않으면 새로고침만으로 숫자가 오르고,
        그 숫자를 근거로 하는 트렌딩 정렬까지 같이 망가진다.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        existing = (
            self.db.query(PostView)
            .filter(PostView.post_id == post_id, PostView.viewer_key == viewer_key)
            .one_or_none()
        )

        if existing:
            fresh = existing.viewed_at and existing.viewed_at > now - timedelta(hours=window_hours)
            existing.viewed_at = now
            # 로그인 전에 봤다가 로그인 후 다시 온 경우 주인을 붙여 준다 (추천 신호).
            if user_id and not existing.user_id:
                existing.user_id = user_id
            self.db.commit()
            if fresh:
                return False
        else:
            self.db.add(
                PostView(
                    id=str(uuid.uuid4()),
                    post_id=post_id,
                    user_id=user_id,
                    viewer_key=viewer_key,
                    viewed_at=now,
                )
            )
            try:
                self.db.commit()
            except IntegrityError:
                # 같은 뷰어의 동시 요청. 상대가 이미 넣었으므로 이번 건은 세지 않는다.
                self.db.rollback()
                return False

        self.increment_view(post_id)
        return True

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

    def list_recommended(
        self, user_id: str, limit: int, offset: int, since_days: int = 90
    ) -> List[Post]:
        """관심 태그 + 팔로우한 사람이 좋아한 글 + 최근성으로 점수를 매긴다.

        좋아요만 보면 신호가 너무 희소하다. 좋아요 3개면 그 3개 태그에 갇히고
        0개면 아무것도 못 준다. 그래서 세 갈래를 섞는다.
          - 관심 태그: 내가 좋아요했거나 읽은 글의 태그. 읽기가 좋아요보다 훨씬 흔하다.
          - 사회적 신호: 내가 팔로우한 사람이 좋아요한 글.
          - 최근성: 반응 점수가 오래된 글에 영원히 밀리지 않도록 감쇠를 준다.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(days=since_days)

        # 관심 신호: 좋아요한 글의 태그 + 최근에 읽은 글의 태그
        liked_posts = select(PostLike.post_id).where(PostLike.user_id == user_id)
        # MariaDB 는 IN (...) 안에 LIMIT 을 못 쓴다.
        # 파생 테이블로 한 번 감싸면 같은 의미로 통과한다.
        recent_views = (
            select(PostView.post_id)
            .where(PostView.user_id == user_id, PostView.viewed_at >= cutoff)
            .order_by(PostView.viewed_at.desc())
            .limit(200)  # 오래된 관심사가 지금 취향을 덮지 않도록 최근 것만
            .subquery()
        )
        viewed_posts = select(recent_views.c.post_id)
        interest_tags = (
            select(PostTag.tag_id)
            .where(or_(PostTag.post_id.in_(liked_posts), PostTag.post_id.in_(viewed_posts)))
            .distinct()
        )

        # 팔로우한 사람들이 좋아요한 글
        following = select(Follow.following_id).where(Follow.follower_id == user_id)
        social_likes = (
            select(PostLike.post_id, func.count().label("n"))
            .where(PostLike.user_id.in_(following))
            .group_by(PostLike.post_id)
            .subquery()
        )
        # 이미 읽은 글은 다시 추천하지 않는다.
        already_seen = select(PostView.post_id).where(PostView.user_id == user_id)

        def capped(column, ceiling: int):
            """상한을 씌운다. 조회수 폭발한 글 하나가 순위를 통째로 먹는 것을 막는다.

            LEAST() 는 MySQL 전용이라 CASE 로 쓴다 (테스트는 SQLite 에서 돈다).
            """
            return case((column > ceiling, ceiling), else_=column)

        # 최근성. 감쇠식 대신 구간 가산으로 둔 이유는 DB 마다 날짜 연산 함수가 달라서다.
        recency = case(
            (Post.published_at >= now - timedelta(days=3), 30),
            (Post.published_at >= now - timedelta(days=7), 20),
            (Post.published_at >= now - timedelta(days=30), 10),
            else_=0,
        )

        score = (
            func.count(func.distinct(PostTag.tag_id)) * 10
            + func.coalesce(social_likes.c.n, 0) * 6
            + capped(Post.like_count, 50) * 2
            + capped(Post.comment_count, 20) * 3
            + recency
        )

        return (
            self.db.query(Post)
            .options(*_LIST_LOADS)
            .outerjoin(PostTag, PostTag.post_id == Post.id)
            .outerjoin(social_likes, social_likes.c.post_id == Post.id)
            .filter(
                Post.status == PostStatus.PUBLISHED,
                Post.user_id != user_id,
                Post.published_at >= cutoff,
                Post.id.notin_(already_seen),
                # 태그가 겹치거나, 내가 팔로우한 사람이 좋아한 글
                or_(PostTag.tag_id.in_(interest_tags), social_likes.c.n.isnot(None)),
            )
            .group_by(Post.id)
            .order_by(score.desc(), Post.published_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

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

    def list_by_stack(
        self,
        name: str,
        version: Optional[str] = None,
        sort: str = "fresh_first",
        limit: int = 20,
        offset: int = 0,
    ) -> List[Post]:
        query = (
            self.db.query(Post)
            .options(*_LIST_LOADS)
            .join(PostStack, PostStack.post_id == Post.id)
            .filter(Post.status == PostStatus.PUBLISHED, PostStack.name == name)
        )
        if version:
            # 18 을 주면 18.x 를 모두 잡는다. 18.3 만 보고 싶으면 그대로 적으면 된다.
            query = query.filter(
                or_(PostStack.version == version, PostStack.version.like(f"{version}.%"))
            )

        if sort == "recent":
            query = query.order_by(Post.published_at.desc())
        elif sort == "trending":
            query = query.order_by(
                (Post.like_count * 3 + Post.comment_count * 2).desc(), Post.published_at.desc()
            )
        else:
            # 기본값이 이것인 게 이 제품의 입장이다.
            # 최신순으로 두면 "최근에 쓴 낡은 글" 이 위로 온다. 독자가 원하는 건
            # 최근에 쓴 글이 아니라 지금도 되는 글이다.
            query = query.order_by(
                func.coalesce(Post.verified_at, Post.published_at).desc(),
                Post.like_count.desc(),
            )

        return query.limit(limit).offset(offset).all()

    def search(self, query: str, limit: int, offset: int) -> List[Post]:
        """제목·요약·본문 전문검색.

        MariaDB 에서는 ngram 파서를 쓴 FULLTEXT 인덱스를 탄다. 기본 파서는 공백으로
        단어를 나눠서 '리액트를' 을 '리액트' 로 못 찾는데, 한국어는 조사가 붙어 다니므로
        그 방식으로는 거의 안 맞는다. ngram 은 2글자 단위로 색인해 이 문제를 피한다.

        SQLite(테스트)에는 이 인덱스가 없으므로 LIKE 로 떨어진다. 결과 집합은 같고
        속도만 다르다.
        """
        term = (query or "").strip()
        if not term:
            return []

        base = self.db.query(Post).options(*_LIST_LOADS).filter(
            Post.status == PostStatus.PUBLISHED
        )

        dialect = self.db.bind.dialect.name if self.db.bind is not None else ""
        if dialect in ("mysql", "mariadb"):
            expression = _boolean_mode_query(term)
            if expression:
                # AGAINST 는 괄호가 필수다. func.match(...).op("AGAINST") 로 조립하면
                # 괄호 없이 렌더되어 문법 오류가 난다.
                match = text(
                    "MATCH (posts.title, posts.summary, posts.content_md) "
                    "AGAINST (:ft_query IN BOOLEAN MODE)"
                ).bindparams(ft_query=expression)
                rows = (
                    base.filter(match)
                    .order_by(Post.published_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                if rows or offset:
                    return rows
                # 토큰 최소 길이(기본 3자) 미만이면 인덱스에 아예 없다. LIKE 로 한 번 더.

        like = f"%{term}%"
        return (
            base.filter(
                or_(Post.title.like(like), Post.summary.like(like), Post.content_md.like(like))
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
