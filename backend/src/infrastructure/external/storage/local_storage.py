"""로컬 디스크 저장소.

개발과 단일 인스턴스 배포용이다. 서버를 2대 이상 띄우면 A 에 올린 파일을 B 가 못 찾고,
컨테이너를 재배포하면 사라진다. 운영에서는 STORAGE_BACKEND=s3 를 쓴다.
"""

from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.output.services.storage_service import StorageService


class LocalStorageService(StorageService):
    def __init__(self, root: Optional[Path] = None, public_prefix: Optional[str] = None):
        self.root = Path(root or settings.UPLOAD_DIR).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_prefix = (public_prefix or settings.UPLOAD_PUBLIC_PREFIX).rstrip("/")

    def _path_for(self, key: str) -> Optional[Path]:
        """key 를 실제 경로로. 루트를 벗어나면 None (경로 탈출 방어선)."""
        target = (self.root / key).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            return None
        return target

    def put(self, key: str, data: bytes, content_type: str) -> str:
        destination = self._path_for(key)
        if destination is None:
            raise ValueError("잘못된 저장 경로입니다.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return self.url_for(key)

    def delete(self, key: str) -> bool:
        target = self._path_for(key)
        if target is None or not target.is_file():
            return False
        target.unlink()
        return True

    def url_for(self, key: str) -> str:
        return f"{self.public_prefix}/{key.lstrip('/')}"

    def key_from_url(self, url: str) -> str:
        prefix = f"{self.public_prefix}/"
        return url[len(prefix):] if url.startswith(prefix) else ""
