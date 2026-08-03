"""Draft(비공개 작업본) → Post(공개 스냅샷) 발행.

발행은 복사다. Draft 는 자동저장으로 계속 바뀌므로, 공개된 글이 편집 중 내용을
실시간으로 따라가면 독자가 읽는 도중 문장이 변하고 캐시 무효화 시점도 잡을 수 없다.
"""

from typing import Any, Dict, List, Optional, Sequence

from src.application.errors import NotFoundError, ValidationError
from src.domain.enums import PostStatus
from src.domain.services.identity import summarize, unique_slug
from src.domain.services.safety_scanner import SafetyScanner
from src.ports.output.repositories.draft_repository import DraftRepository
from src.ports.output.repositories.post_repository import PostRepository
from src.ports.output.repositories.taxonomy_repository import TagRepository
from src.ports.output.repositories.user_repository import UserRepository

MIN_TITLE = 1
MIN_BODY_CHARS = 30


class PublishPostUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        post_repo: PostRepository,
        tag_repo: TagRepository,
        user_repo: UserRepository,
    ):
        self.draft_repo = draft_repo
        self.post_repo = post_repo
        self.tag_repo = tag_repo
        self.user_repo = user_repo
        self.scanner = SafetyScanner()

    def execute(
        self,
        user_id: str,
        draft_id: str,
        title: str,
        tags: Sequence[str] = (),
        cover_url: Optional[str] = None,
        allow_sensitive: bool = False,
    ) -> Dict[str, Any]:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        if not user.handle:
            # 공개 주소가 /@handle/slug 라서 handle 없이는 URL 을 만들 수 없다.
            raise ValidationError("발행하려면 먼저 블로그 아이디(@handle)를 정해야 합니다.")

        draft = self.draft_repo.get_by_id(draft_id)
        if not draft or draft.user_id != user_id:
            raise NotFoundError("Draft 를 찾을 수 없습니다.")

        version = self.draft_repo.get_latest_version(draft_id)
        if not version or not (version.content_md or "").strip():
            raise ValidationError("내용이 비어 있어 발행할 수 없습니다.")

        title = (title or "").strip()
        if len(title) < MIN_TITLE:
            raise ValidationError("제목을 입력해주세요.")

        content = version.content_md
        if len(content.strip()) < MIN_BODY_CHARS:
            raise ValidationError(f"본문이 너무 짧습니다 (최소 {MIN_BODY_CHARS}자).")

        # 공개되는 순간 되돌릴 수 없으므로, 민감정보는 기본적으로 발행을 막는다.
        findings = self.scanner.scan(content)
        blocking = [f for f in findings if f["severity"] == "high"]
        if blocking and not allow_sensitive:
            raise ValidationError(
                f"민감정보로 보이는 값이 {len(blocking)}건 있습니다. "
                "Safety 탭에서 처리하거나 확인 후 다시 시도해주세요."
            )

        existing = self.post_repo.get_by_draft_id(draft_id)
        slug = unique_slug(
            title,
            self.post_repo.slugs_for_user(user_id),
            current=existing.slug if existing else None,
        )
        summary = summarize(content)

        if existing:
            # 재발행: 주소를 유지한다. 이미 걸린 외부 링크와 색인을 지키기 위해서다.
            post = self.post_repo.update_content(
                post_id=existing.id,
                title=title,
                content_md=content,
                summary=summary,
                slug=existing.slug,
                cover_url=cover_url,
            )
            if existing.status is not PostStatus.PUBLISHED:
                post = self.post_repo.set_status(post.id, PostStatus.PUBLISHED)
                self.user_repo.adjust_post_count(user_id, 1)
            created = False
        else:
            post = self.post_repo.create(
                user_id=user_id,
                draft_id=draft_id,
                slug=slug,
                title=title,
                content_md=content,
                summary=summary,
                cover_url=cover_url,
            )
            self.user_repo.adjust_post_count(user_id, 1)
            created = True

        saved_tags = self.tag_repo.set_for_post(post.id, list(tags))

        return {
            "id": post.id,
            "slug": post.slug,
            "url": f"/@{user.handle}/{post.slug}",
            "status": post.status.value,
            "created": created,
            "tags": [t.display_name for t in saved_tags],
            "sensitive_findings": len(blocking),
            "cover_url": post.cover_url,
        }


class UnpublishPostUseCase:
    """발행 취소. 행을 지우지 않고 내려서 재발행 시 주소를 유지한다."""

    def __init__(
        self,
        post_repo: PostRepository,
        user_repo: UserRepository,
    ):
        self.post_repo = post_repo
        self.user_repo = user_repo

    def execute(self, user_id: str, post_id: str) -> Dict[str, Any]:
        post = self.post_repo.get_by_id(post_id)
        if not post or post.user_id != user_id:
            raise NotFoundError("글을 찾을 수 없습니다.")

        if post.status is PostStatus.PUBLISHED:
            self.user_repo.adjust_post_count(user_id, -1)

        updated = self.post_repo.set_status(post_id, PostStatus.UNLISTED)
        return {"id": updated.id, "status": updated.status.value}


class DeletePostUseCase:
    def __init__(
        self,
        post_repo: PostRepository,
        tag_repo: TagRepository,
        user_repo: UserRepository,
    ):
        self.post_repo = post_repo
        self.tag_repo = tag_repo
        self.user_repo = user_repo

    def execute(self, user_id: str, post_id: str) -> Dict[str, Any]:
        post = self.post_repo.get_by_id(post_id)
        if not post or post.user_id != user_id:
            raise NotFoundError("글을 찾을 수 없습니다.")

        was_published = post.status is PostStatus.PUBLISHED
        # 태그 카운터를 먼저 정리해야 고아 카운트가 남지 않는다.
        self.tag_repo.clear_for_post(post_id)
        self.post_repo.delete(post_id)
        if was_published:
            self.user_repo.adjust_post_count(user_id, -1)

        return {"deleted": True}
