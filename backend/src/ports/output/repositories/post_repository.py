from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Sequence

from src.domain.enums import PostStatus

if TYPE_CHECKING:
    from src.infrastructure.database.models.post import Post


class PostRepository(ABC):
    """공개 발행물 저장소.

    공개 조회 경로는 인증이 없고 트래픽이 몰리므로, 목록은 항상 페이지네이션과
    상태 필터를 강제한다.
    """

    @abstractmethod
    def create(
        self,
        user_id: str,
        draft_id: Optional[str],
        slug: str,
        title: str,
        content_md: str,
        summary: str,
        cover_url: Optional[str] = None,
    ) -> "Post":
        ...

    @abstractmethod
    def update_content(
        self,
        post_id: str,
        title: str,
        content_md: str,
        summary: str,
        slug: Optional[str] = None,
        cover_url: Optional[str] = None,
    ) -> "Post":
        ...

    @abstractmethod
    def set_status(self, post_id: str, status: PostStatus) -> "Post":
        ...

    @abstractmethod
    def get_by_id(self, post_id: str) -> Optional["Post"]:
        ...

    @abstractmethod
    def get_by_draft_id(self, draft_id: str) -> Optional["Post"]:
        ...

    @abstractmethod
    def get_public(self, handle: str, slug: str) -> Optional["Post"]:
        """공개 글 1건. 발행 상태가 아니면 None."""
        ...

    @abstractmethod
    def slugs_for_user(self, user_id: str) -> List[str]:
        ...

    @abstractmethod
    def list_by_user(
        self, user_id: str, only_published: bool, limit: int, offset: int
    ) -> List["Post"]:
        ...

    @abstractmethod
    def count_by_user(self, user_id: str, only_published: bool) -> int:
        ...

    @abstractmethod
    def list_feed(
        self,
        limit: int,
        offset: int,
        sort: str = "recent",
        tag: Optional[str] = None,
        since_days: Optional[int] = None,
        exclude_user_ids: Sequence[str] = (),
    ) -> List["Post"]:
        """공개 피드. sort 는 recent | trending."""
        ...

    @abstractmethod
    def list_recommended(
        self, user_id: str, limit: int, offset: int, since_days: int = 90
    ) -> List["Post"]:
        """내가 좋아요한 글의 태그와 겹치는 다른 사람의 글.

        추천이라는 이름을 붙였지만 학습 모델이 아니라 태그 겹침 + 반응 가중치다.
        신호가 없는 사용자에게는 호출자가 트렌딩으로 대체해야 한다.
        """
        ...

    @abstractmethod
    def list_following_feed(
        self, user_id: str, limit: int, offset: int
    ) -> List["Post"]:
        ...

    @abstractmethod
    def search(self, query: str, limit: int, offset: int) -> List["Post"]:
        ...

    @abstractmethod
    def all_published_for_sitemap(self, limit: int = 50_000) -> List["Post"]:
        ...

    @abstractmethod
    def increment_view(self, post_id: str) -> None:
        ...

    @abstractmethod
    def delete(self, post_id: str) -> None:
        ...
