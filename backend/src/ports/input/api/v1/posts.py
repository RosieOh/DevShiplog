"""발행 관리 (인증 필요). 공개 조회는 public.py 가 담당한다."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from src.application.use_cases.post.publish_post import (
    DeletePostUseCase,
    PublishPostUseCase,
    UnpublishPostUseCase,
)
from src.ports.input.api.v1.dependencies import (
    client_identity,
    enforce_rate_limit,
    get_current_user_id,
    get_draft_repo,
    get_post_repo,
    get_tag_repo,
    get_user_repo,
)
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.taxonomy_repository import TagRepository
from src.infrastructure.external import revalidation
from src.ports.output.repositories.user_repository import UserRepository

router = APIRouter()


class PublishRequest(BaseModel):
    draft_id: str
    title: str = Field(min_length=1, max_length=300)
    tags: List[str] = Field(default_factory=list, max_length=10)
    cover_url: Optional[str] = None
    # 민감정보 경고를 확인하고도 진행하겠다는 명시적 동의
    allow_sensitive: bool = False


class PublishResponse(BaseModel):
    id: str
    slug: str
    url: str
    status: str
    created: bool
    tags: List[str]
    sensitive_findings: int


@router.post("", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
def publish(
    request: Request,
    payload: PublishRequest,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    draft_repo: DraftRepository = Depends(get_draft_repo),
    post_repo: PostRepository = Depends(get_post_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """작업본을 공개 발행한다. 같은 작업본을 다시 발행하면 주소를 유지한 채 갱신된다."""
    enforce_rate_limit("post_publish", client_identity(request, user_id))

    use_case = PublishPostUseCase(draft_repo, post_repo, tag_repo, user_repo)
    result = use_case.execute(
        user_id=user_id,
        draft_id=payload.draft_id,
        title=payload.title,
        tags=payload.tags,
        cover_url=payload.cover_url,
        allow_sensitive=payload.allow_sensitive,
    )

    # 공개 페이지 캐시를 깬다. 응답을 막지 않도록 백그라운드로 보낸다.
    user = user_repo.get_by_id(user_id)
    background.add_task(
        revalidation.notify,
        revalidation.tags_for_post(user.handle if user else None, result["slug"]),
    )
    return result


@router.get("/mine")
def my_posts(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """내 발행 목록. 내려둔 글(unlisted)도 함께 보여준다."""
    user = user_repo.get_by_id(user_id)
    posts = post_repo.list_by_user(user_id, only_published=False, limit=limit, offset=offset)
    return [
        {
            "id": p.id,
            "slug": p.slug,
            "title": p.title,
            "status": p.status.value,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "like_count": p.like_count,
            "comment_count": p.comment_count,
            "view_count": p.view_count,
            "url": f"/@{user.handle}/{p.slug}" if user and user.handle else None,
            "draft_id": p.draft_id,
        }
        for p in posts
    ]


@router.get("/by-draft/{draft_id}")
def post_for_draft(
    draft_id: str,
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """편집 화면에서 "이 작업본이 이미 발행됐는지" 확인할 때 쓴다."""
    post = post_repo.get_by_draft_id(draft_id)
    if not post or post.user_id != user_id:
        return {"published": False}

    user = user_repo.get_by_id(user_id)
    return {
        "published": True,
        "id": post.id,
        "slug": post.slug,
        "title": post.title,
        "status": post.status.value,
        "tags": [t.display_name for t in tag_repo.list_for_post(post.id)],
        "url": f"/@{user.handle}/{post.slug}" if user and user.handle else None,
    }


@router.post("/{post_id}/unpublish")
def unpublish(
    post_id: str,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    post = post_repo.get_by_id(post_id)
    slug = post.slug if post else None
    result = UnpublishPostUseCase(post_repo, user_repo).execute(user_id, post_id)

    user = user_repo.get_by_id(user_id)
    background.add_task(
        revalidation.notify,
        revalidation.tags_for_post(user.handle if user else None, slug),
    )
    return result


@router.delete("/{post_id}")
def delete_post(
    post_id: str,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    user_repo: UserRepository = Depends(get_user_repo),
):
    post = post_repo.get_by_id(post_id)
    slug = post.slug if post else None
    result = DeletePostUseCase(post_repo, tag_repo, user_repo).execute(user_id, post_id)

    user = user_repo.get_by_id(user_id)
    background.add_task(
        revalidation.notify,
        revalidation.tags_for_post(user.handle if user else None, slug),
    )
    return result
