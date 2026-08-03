from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:  # 런타임에는 infrastructure 를 import 하지 않는다 (의존성 방향 유지)
    from src.infrastructure.database.models.draft import Draft
    from src.infrastructure.database.models.draft_version import DraftVersion


class DraftRepository(ABC):
    @abstractmethod
    def create(
        self,
        user_id: str,
        draft_type: str,
        audience: str,
        length_preset: str,
        style_profile_id: Optional[str] = None,
    ) -> "Draft":
        ...

    @abstractmethod
    def get_by_id(self, draft_id: str) -> Optional["Draft"]:
        ...

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> List["Draft"]:
        ...

    @abstractmethod
    def create_version(
        self,
        draft_id: str,
        version_no: int,
        content_md: str,
        meta_json: Optional[dict] = None,
    ) -> "DraftVersion":
        ...

    @abstractmethod
    def update_version_content(
        self,
        version_id: str,
        content_md: str,
        meta_json: Optional[dict] = None,
    ) -> "DraftVersion":
        """기존 버전을 제자리에서 수정한다 (자동저장용 — 새 버전을 만들지 않음)."""
        ...

    @abstractmethod
    def get_version_by_id(self, version_id: str) -> Optional["DraftVersion"]:
        ...

    @abstractmethod
    def get_latest_version(self, draft_id: str) -> Optional["DraftVersion"]:
        ...

    @abstractmethod
    def get_versions(self, draft_id: str) -> List["DraftVersion"]:
        ...

    @abstractmethod
    def next_version_no(self, draft_id: str) -> int:
        ...
