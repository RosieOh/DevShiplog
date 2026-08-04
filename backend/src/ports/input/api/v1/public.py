"""공개 API — 인증 없음.

블로그 플랫폼 트래픽의 대부분은 로그인하지 않은 독자와 검색 크롤러다.
이 라우터는 절대 인증을 요구하지 않으며, 반환값에 비공개 정보를 담지 않는다.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from src.ports.input.api.v1.dependencies import (
    get_block_repo,
    get_comment_repo,
    get_follow_repo,
    get_like_repo,
    get_optional_user_id,
    get_post_repo,
    get_series_repo,
    get_tag_repo,
    get_user_repo,
    viewer_key,
)
from src.ports.output.repositories.moderation_repository import BlockRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.social_repository import (
    CommentRepository,
    FollowRepository,
    LikeRepository,
)
from src.ports.output.repositories.taxonomy_repository import SeriesRepository, TagRepository
from src.ports.output.repositories.user_repository import UserRepository

router = APIRouter()

MAX_PAGE_SIZE = 50


def _author(user) -> Dict[str, Any]:
    """공개해도 되는 작성자 정보만. 이메일은 절대 나가지 않는다."""
    return {
        "handle": user.handle,
        "display_name": user.display_name or user.handle,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
    }


def _post_card(post) -> Dict[str, Any]:
    """목록용. 본문 전체를 싣지 않는다."""
    return {
        "id": post.id,
        "slug": post.slug,
        "title": post.title,
        "summary": post.summary,
        "cover_url": post.cover_url,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "tags": [link.tag.display_name for link in post.tags],
        "author": _author(post.user),
        "url": f"/@{post.user.handle}/{post.slug}",
    }


class PostList(BaseModel):
    items: List[Dict[str, Any]]
    has_more: bool


def _paged(items: List, limit: int) -> Dict[str, Any]:
    # limit+1 을 조회해 다음 페이지 존재 여부를 판단한다 (전체 COUNT 를 피한다).
    return {"items": [_post_card(p) for p in items[:limit]], "has_more": len(items) > limit}


# ------------------------------------------------------------------- 피드


# 트렌딩 기간 선택지 (Velog 의 "이번 주" 드롭다운에 해당)
PERIOD_DAYS = {"week": 7, "month": 30, "year": 365, "all": None}


@router.get("/feed", response_model=PostList)
def feed(
    sort: str = Query("recent", pattern="^(recent|trending|recommended|following)$"),
    period: str = Query("week", pattern="^(week|month|year|all)$"),
    tag: Optional[str] = None,
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    viewer_id: Optional[str] = Depends(get_optional_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    block_repo: BlockRepository = Depends(get_block_repo),
):
    """홈 피드.

    - recent      : 최신순
    - trending    : 반응 가중치 + 기간 필터
    - recommended : 내가 좋아요한 글의 태그와 겹치는 글 (로그인 필요, 없으면 트렌딩)
    - following   : 내가 팔로우한 사람의 글 (로그인 필요, 없으면 최신)
    """
    # 차단한 사람의 글은 내 화면에서 빠져야 한다.
    blocked = block_repo.blocked_ids(viewer_id) if viewer_id else []

    if sort == "following":
        if not viewer_id:
            return _paged(post_repo.list_feed(limit=limit + 1, offset=offset), limit)
        return _paged(post_repo.list_following_feed(viewer_id, limit + 1, offset), limit)

    if sort == "recommended":
        if viewer_id:
            posts = post_repo.list_recommended(viewer_id, limit + 1, offset)
            if posts:
                return _paged(posts, limit)
        # 신호가 없으면 트렌딩으로 대체한다. 빈 화면을 보여주는 것보다 낫다.
        sort = "trending"

    posts = post_repo.list_feed(
        limit=limit + 1,
        offset=offset,
        sort=sort,
        tag=tag,
        # 인기순은 최근 글 중에서만 뽑는다. 아니면 오래된 글이 상단을 영구 점유한다.
        since_days=PERIOD_DAYS[period] if sort == "trending" else None,
        exclude_user_ids=blocked,
    )
    return _paged(posts, limit)


@router.get("/search", response_model=PostList)
def search(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    post_repo: PostRepository = Depends(get_post_repo),
):
    return _paged(post_repo.search(q, limit + 1, offset), limit)


@router.get("/tags")
def popular_tags(
    limit: int = Query(30, ge=1, le=100),
    tag_repo: TagRepository = Depends(get_tag_repo),
):
    return [
        {"name": t.name, "display_name": t.display_name, "post_count": t.post_count}
        for t in tag_repo.list_popular(limit)
    ]


# --------------------------------------------------------------- 블로그 / 글


@router.get("/blogs/{handle}")
def blog_home(
    handle: str,
    viewer_id: Optional[str] = Depends(get_optional_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
    post_repo: PostRepository = Depends(get_post_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    follow_repo: FollowRepository = Depends(get_follow_repo),
):
    user = user_repo.get_by_handle(handle)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="블로그를 찾을 수 없습니다.")

    return {
        **_author(user),
        "post_count": post_repo.count_by_user(user.id, only_published=True),
        "follower_count": user.follower_count,
        "following_count": user.following_count,
        "series": [
            {"slug": s.slug, "name": s.name, "post_count": len(s.posts)}
            for s in series_repo.list_by_user(user.id)
        ],
        # 로그인한 사람이 볼 때만 채워지는 개인화 값
        "is_following": bool(viewer_id) and follow_repo.exists(viewer_id, user.id),
        "is_me": viewer_id == user.id,
    }


@router.get("/blogs/{handle}/posts", response_model=PostList)
def blog_posts(
    handle: str,
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    user_repo: UserRepository = Depends(get_user_repo),
    post_repo: PostRepository = Depends(get_post_repo),
):
    user = user_repo.get_by_handle(handle)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="블로그를 찾을 수 없습니다.")
    posts = post_repo.list_by_user(user.id, only_published=True, limit=limit + 1, offset=offset)
    return _paged(posts, limit)


@router.get("/blogs/{handle}/posts/{slug}")
def post_detail(
    request: Request,
    handle: str,
    slug: str,
    viewer_id: Optional[str] = Depends(get_optional_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    like_repo: LikeRepository = Depends(get_like_repo),
    follow_repo: FollowRepository = Depends(get_follow_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
):
    post = post_repo.get_public(handle, slug)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="글을 찾을 수 없습니다.")

    # 같은 사람의 재방문은 24시간 안에서 한 번만 센다. 새로고침으로 오르는 숫자는
    # 아무 의미가 없고, 그 숫자를 근거로 하는 트렌딩 정렬까지 같이 망가진다.
    post_repo.record_view(post.id, viewer_key(request, viewer_id), viewer_id)

    series_context = series_repo.context_for_post(post.id)

    comments = comment_repo.list_for_post(post.id)
    roots = [c for c in comments if c.parent_id is None]
    replies: Dict[str, List] = {}
    for c in comments:
        if c.parent_id:
            replies.setdefault(c.parent_id, []).append(c)

    def render(comment) -> Dict[str, Any]:
        deleted = comment.deleted_at is not None
        return {
            "id": comment.id,
            # 답글이 달린 댓글은 자리를 남긴다. 내용만 가린다.
            "body": None if deleted else comment.body,
            "deleted": deleted,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "author": None if deleted else _author(comment.user),
            "is_mine": bool(viewer_id) and comment.user_id == viewer_id,
            "replies": [render(r) for r in replies.get(comment.id, [])],
        }

    return {
        **_post_card(post),
        "content_md": post.content_md,
        "view_count": post.view_count,
        "comments": [render(c) for c in roots],
        "is_liked": bool(viewer_id) and like_repo.exists(post.id, viewer_id),
        "is_following_author": bool(viewer_id) and follow_repo.exists(viewer_id, post.user_id),
        "is_mine": viewer_id == post.user_id,
        "series": _series_nav(series_context, handle),
    }


def _series_nav(context: Optional[Dict[str, Any]], handle: str) -> Optional[Dict[str, Any]]:
    """시리즈 앞뒤 네비게이션. 시리즈에 속하지 않으면 None."""
    if not context:
        return None

    def link(p) -> Optional[Dict[str, Any]]:
        return {"title": p.title, "url": f"/@{handle}/{p.slug}"} if p else None

    series = context["series"]
    return {
        "name": series.name,
        "url": f"/@{handle}/series/{series.slug}",
        "position": context["position"],
        "total": context["total"],
        "previous": link(context["previous"]),
        "next": link(context["next"]),
    }


@router.get("/blogs/{handle}/series/{series_slug}")
def series_detail(
    handle: str,
    series_slug: str,
    user_repo: UserRepository = Depends(get_user_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
):
    series = series_repo.get_public(handle, series_slug)
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="시리즈를 찾을 수 없습니다.")

    user = user_repo.get_by_handle(handle)
    ordered = [link.post for link in series.posts if link.post is not None]
    return {
        "slug": series.slug,
        "name": series.name,
        "description": series.description,
        "author": _author(user),
        "items": [_post_card(p) for p in ordered],
    }


# ------------------------------------------------------------------- SEO


@router.get("/sitemap")
def sitemap(post_repo: PostRepository = Depends(get_post_repo)):
    """프론트의 sitemap.xml 생성에 쓸 원본 목록."""
    return [
        {
            "url": f"/@{p.user.handle}/{p.slug}",
            "updated_at": (p.updated_at or p.published_at).isoformat()
            if (p.updated_at or p.published_at)
            else None,
        }
        for p in post_repo.all_published_for_sitemap()
        if p.user and p.user.handle
    ]


@router.get("/blogs/{handle}/rss")
def blog_rss_source(
    handle: str,
    user_repo: UserRepository = Depends(get_user_repo),
    post_repo: PostRepository = Depends(get_post_repo),
):
    """RSS 생성용 원본. 우리가 남의 RSS 를 읽던 입장에서 이제 내보내는 쪽이 된다."""
    user = user_repo.get_by_handle(handle)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="블로그를 찾을 수 없습니다.")

    posts = post_repo.list_by_user(user.id, only_published=True, limit=30, offset=0)
    return {
        "author": _author(user),
        "items": [
            {
                "title": p.title,
                "url": f"/@{user.handle}/{p.slug}",
                "summary": p.summary,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
            for p in posts
        ],
    }
