from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class StoredFile:
    """저장 결과.

    url 은 브라우저가 바로 쓸 수 있는 공개 주소다.
    variants 는 파생본 주소 (예: {"w1200": "...", "w400": "..."}).
    """

    url: str
    key: str
    size: int
    content_type: str
    variants: Dict[str, str] = field(default_factory=dict)


class StorageService(ABC):
    """업로드 저장소 — 이름 그대로 바이트를 넣고 빼는 곳이다.

    형식 판별·리사이징·키 작명은 여기서 하지 않는다. 그건 업로드 유스케이스의 일이고,
    저장소를 로컬에서 S3 로 바꿔도 달라지지 않아야 하는 규칙이기 때문이다.
    """

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> str:
        """바이트를 key 에 저장하고 공개 URL 을 돌려준다."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """지웠으면 True. 없으면 False (예외를 던지지 않는다)."""

    @abstractmethod
    def url_for(self, key: str) -> str:
        """저장하지 않고 key 의 공개 URL 만 만든다."""

    def delete_by_url(self, url: str) -> bool:
        """공개 URL 로 지운다. DB 에는 key 가 아니라 URL 이 남아 있어서 필요하다."""
        key = self.key_from_url(url)
        return self.delete(key) if key else False

    @abstractmethod
    def key_from_url(self, url: str) -> str:
        """공개 URL → key. 우리 저장소가 만든 주소가 아니면 빈 문자열."""
