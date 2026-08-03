from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredFile:
    """저장 결과. url 은 브라우저가 바로 쓸 수 있는 공개 주소다."""

    url: str
    key: str
    size: int
    content_type: str


class StorageService(ABC):
    """업로드 저장소.

    지금은 로컬 디스크 구현만 있다. S3 로 옮길 때 이 인터페이스만 다시 구현하면
    호출부(유스케이스·라우터)는 손대지 않는다.
    """

    @abstractmethod
    def save(self, data: bytes, filename: str, content_type: str, prefix: str = "") -> StoredFile:
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        ...
