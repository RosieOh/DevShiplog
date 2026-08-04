"""발행 관리 (인증 필요). 공개 조회는 public.py 가 담당한다."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

from src.infrastructure.config.settings import settings

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


def _cleanup_orphan(url: Optional[str]) -> None:
    """참조가 사라진 업로드 파일을 지운다.

    반드시 캐시 무효화 뒤에 호출한다. 먼저 지우면, 아직 옛 커버를 가리키는
    캐시된 목록 페이지가 깨진 이미지를 내보내는 구간이 생긴다.
    정리는 부가작업이라 실패해도 조용히 넘어간다.
    """
    if not url:
        return
    try:
        from src.application.use_cases.upload.upload_image import DeleteUploadUseCase
        from src.infrastructure.external.storage import get_storage

        DeleteUploadUseCase(get_storage()).execute(url)
    except Exception:
        pass


class PublishRequest(BaseModel):
    draft_id: str
    title: str = Field(min_length=1, max_length=300)
    tags: List[str] = Field(default_factory=list, max_length=10)
    cover_url: Optional[str] = Field(default=None, max_length=1000)
    # 민감정보 경고를 확인하고도 진행하겠다는 명시적 동의
    allow_sensitive: bool = False

    @field_validator("cover_url")
    @classmethod
    def _cover_must_be_safe(cls, value: Optional[str]) -> Optional[str]:
        """커버 주소는 우리 저장소이거나 https 여야 한다.

        클라이언트가 보낸 문자열이 그대로 <img src> 와 og:image 에 들어간다.
        검사하지 않으면 javascript:/data: 스킴이나 남의 추적 픽셀을 우리 글에 심을 수 있다.

        허용 목록은 세 가지다.
        - 우리 오브젝트 저장소 주소 (MinIO/S3). 개발에서는 http://localhost:9000/... 이라
          https 만 허용하면 자기 업로드가 거절된다.
        - 로컬 백엔드의 /uploads/... 경로
        - 그 외 외부 이미지는 https 만 (평문 http 는 혼합 콘텐츠로 차단된다)
        """
        if value is None or value == "":
            return None

        allowed_prefixes = [f"{settings.UPLOAD_PUBLIC_PREFIX.rstrip('/')}/"]
        if settings.STORAGE_PUBLIC_BASE_URL:
            allowed_prefixes.append(f"{settings.STORAGE_PUBLIC_BASE_URL.rstrip('/')}/")

        if any(value.startswith(p) for p in allowed_prefixes) or value.startswith("https://"):
            return value
        raise ValueError("커버 이미지 주소가 올바르지 않습니다.")


class PublishResponse(BaseModel):
    id: str
    slug: str
    url: str
    status: str
    created: bool
    tags: List[str]
    sensitive_findings: int
    # 호출자가 방금 올린 커버가 실제로 붙었는지 응답만 보고 확인할 수 있어야 한다.
    cover_url: Optional[str] = None


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
    # BackgroundTasks 는 등록 순서대로 돈다. 무효화 뒤에 파일을 지운다.
    background.add_task(_cleanup_orphan, result.pop("orphan_cover_url", None))
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
    background.add_task(_cleanup_orphan, result.pop("orphan_cover_url", None))
    return result
