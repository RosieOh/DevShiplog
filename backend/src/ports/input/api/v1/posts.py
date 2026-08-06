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
    get_notification_repo,
    get_tag_repo,
    get_user_repo,
)
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.taxonomy_repository import TagRepository
from src.infrastructure.external import revalidation
from src.ports.output.repositories.user_repository import UserRepository
from src.application.use_cases.post import tech_stack as stack_service
from src.application.use_cases.metrics import product_metrics as metrics
from src.infrastructure.database.session import get_db
from sqlalchemy.orm import Session

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
    # 이 글이 전제하는 기술과 버전. [{"name": "react", "version": "18.3"}]
    # 생략하면 본문에서 자동 추출한 것을 그대로 쓴다.
    stacks: Optional[List[Dict[str, Any]]] = Field(default=None, max_length=12)
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
    stacks: List[Dict[str, Any]] = []


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
    db: Session = Depends(get_db),
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

    # 기술 스택. 안 보내면 본문에서 뽑은 것을 그대로 쓴다 —
    # 아무것도 없는 것보다는 추출본이 낫고, 작성자가 나중에 고칠 수 있다.
    draft_version = draft_repo.get_latest_version(payload.draft_id)
    stacks = payload.stacks
    if stacks is None:
        stacks = stack_service.suggest(draft_version.content_md if draft_version else "")
    saved_stacks = stack_service.replace_stacks(db, result["id"], stacks)
    result["stacks"] = [{"name": s.name, "version": s.version} for s in saved_stacks]

    # 자동 추출이 쓸 만한지 판단하려면 "제안한 것" 과 "확정한 것" 을 비교해야 한다.
    # 보정률이 0% 면 추출이 완벽하거나 아무도 안 본 것이고, 둘은 전혀 다른 상황이다.
    suggested = stack_service.suggest(draft_version.content_md if draft_version else "")
    metrics.record(
        db,
        metrics.STACK_CONFIRMED,
        user_id=user_id,
        post_id=result["id"],
        suggested_count=len(suggested),
        confirmed_count=len(saved_stacks),
        corrected=sorted((s["name"], s["version"]) for s in suggested)
        != sorted((s.name, s.version) for s in saved_stacks),
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


# ------------------------------------------------------- 기술 스택 · 검증


class StackItem(BaseModel):
    name: str = Field(max_length=40)
    version: Optional[str] = Field(default=None, max_length=20)


class SignalRequest(BaseModel):
    kind: str  # works | broken
    note: Optional[str] = Field(default=None, max_length=1000)


@router.post("/stacks/suggest")
def suggest_stacks(
    payload: Dict[str, Any],
    user_id: str = Depends(get_current_user_id),
):
    """본문에서 기술 스택 후보를 뽑는다.

    발행 화면이 저장 전에 미리 보여주기 위한 것이라 글에 붙이지 않는다.
    확정은 작성자가 발행할 때 한다 — 자동으로 확정하면 틀린 메타데이터가
    조용히 퍼지고, 그건 없는 것보다 나쁘다.
    """
    return {"stacks": stack_service.suggest(str(payload.get("content_md", "")))}


@router.put("/{post_id}/stacks")
def update_stacks(
    post_id: str,
    stacks: List[StackItem],
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    db: Session = Depends(get_db),
):
    """스택을 통째로 갈아끼운다."""
    post = post_repo.get_by_id(post_id)
    if not post or post.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="글을 찾을 수 없습니다.")

    saved = stack_service.replace_stacks(db, post_id, [s.model_dump() for s in stacks])
    user = user_repo.get_by_id(user_id)
    background.add_task(
        revalidation.notify, revalidation.tags_for_post(user.handle if user else None, post.slug)
    )
    return {"stacks": [{"name": s.name, "version": s.version} for s in saved]}


@router.post("/{post_id}/verify")
def verify_post(
    post_id: str,
    background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    db: Session = Depends(get_db),
):
    """"지금도 동작한다" 를 기록한다.

    글을 고치지 않아도 누를 수 있다. 확인은 편집과 다른 행위이고,
    "다시 돌려봤고 그대로 됐다" 는 것 자체가 독자에게 주는 정보다.
    """
    result = stack_service.mark_verified(db, post_id, user_id)

    post = post_repo.get_by_id(post_id)
    user = user_repo.get_by_id(user_id)
    background.add_task(
        revalidation.notify,
        revalidation.tags_for_post(user.handle if user else None, post.slug if post else None),
    )
    return result


@router.get("/needs-update")
def posts_needing_update(
    user_id: str = Depends(get_current_user_id),
    post_repo: PostRepository = Depends(get_post_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    db: Session = Depends(get_db),
):
    """갱신이 필요한 내 글.

    "낡은 글이 있다" 만으로는 아무도 안 고친다. 무엇부터 고쳐야 하는지가 있어야 한다.
    그래서 신호 수와 조회수로 정렬한다 — 안 읽히는 낡은 글은 급하지 않다.
    """
    user = user_repo.get_by_id(user_id)
    posts = post_repo.list_by_user(user_id, only_published=True, limit=200, offset=0)

    items = []
    for post in posts:
        freshness = stack_service.freshness_of(post)
        signals = stack_service.signal_summary(db, post.id)
        unresolved_broken = signals["broken"] > 0
        if freshness["level"] in ("fresh",) and not unresolved_broken:
            continue
        items.append(
            {
                "id": post.id,
                "title": post.title,
                "url": f"/@{user.handle}/{post.slug}" if user and user.handle else None,
                "view_count": post.view_count,
                "freshness": freshness,
                "stacks": stack_service.stacks_of(post),
                "signals": signals,
            }
        )

    # 안 읽히는 낡은 글보다, 읽히는데 안 되는 글이 급하다.
    severity = {"stale": 0, "aging": 1, "unverified": 2, "fresh": 3}
    items.sort(
        key=lambda i: (
            0 if i["signals"]["broken"] else 1,
            severity.get(i["freshness"]["level"], 9),
            -i["view_count"],
        )
    )
    return {"items": items}


@router.post("/{post_id}/signal")
def send_signal(
    post_id: str,
    request: Request,
    payload: SignalRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    notification_repo=Depends(get_notification_repo),
):
    """독자가 "따라 해봤다" 를 알린다."""
    enforce_rate_limit("signal", client_identity(request, user_id))
    return stack_service.send_signal(
        db, post_id, user_id, payload.kind, payload.note, notification_repo
    )


@router.get("/metrics/product")
def product_metrics_summary(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """신선도 기능이 실제로 값어치가 있는가.

    지금은 로그인한 사람이면 볼 수 있게 열어 둔다. 운영자 개념이 아직 없고,
    개인정보가 아니라 집계값만 나가기 때문이다. 운영자 역할이 생기면 좁힌다.

    숫자만 보면 "나쁘지 않네" 로 넘어가게 되므로 판정을 같이 낸다.
    """
    return metrics.summary(db)
