"""로컬 디스크 업로드 저장소.

보안상 중요한 두 가지:
1) 확장자와 Content-Type 은 클라이언트가 마음대로 보낸다. 실제 바이트의 매직 넘버로
   판별해야 한다. 안 그러면 image/png 라고 주장하는 HTML 을 올려 저장형 XSS 가 된다.
2) 파일명은 절대 그대로 쓰지 않는다. `../../etc/passwd` 같은 경로 탈출을 막기 위해
   무작위 이름을 새로 만든다.
"""

import secrets
from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.ports.output.services.storage_service import StoredFile, StorageService

# 매직 넘버 → (확장자, 정규화된 MIME)
_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"GIF87a", "gif", "image/gif"),
    (b"GIF89a", "gif", "image/gif"),
]


class UnsupportedFileError(ValueError):
    """허용하지 않는 파일 형식"""


def sniff_image(data: bytes) -> tuple[str, str]:
    """바이트를 보고 이미지 형식을 판별한다. 아니면 예외."""
    for signature, ext, mime in _SIGNATURES:
        if data.startswith(signature):
            return ext, mime

    # WebP: "RIFF....WEBP"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"

    raise UnsupportedFileError("PNG, JPEG, GIF, WebP 이미지만 올릴 수 있습니다.")


class LocalStorageService(StorageService):
    def __init__(self, root: Optional[Path] = None, public_prefix: Optional[str] = None):
        self.root = Path(root or settings.UPLOAD_DIR).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_prefix = (public_prefix or settings.UPLOAD_PUBLIC_PREFIX).rstrip("/")

    def save(self, data: bytes, filename: str, content_type: str, prefix: str = "") -> StoredFile:
        if not data:
            raise UnsupportedFileError("빈 파일입니다.")
        if len(data) > settings.MAX_UPLOAD_BYTES:
            limit_mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
            raise UnsupportedFileError(f"파일이 너무 큽니다 (최대 {limit_mb}MB).")

        # 클라이언트가 준 이름·타입은 신뢰하지 않는다.
        ext, mime = sniff_image(data)

        safe_prefix = "".join(c for c in prefix if c.isalnum() or c in "-_")
        key = f"{safe_prefix + '/' if safe_prefix else ''}{secrets.token_urlsafe(16)}.{ext}"

        destination = (self.root / key).resolve()
        # 경로 탈출 최종 방어선
        if not str(destination).startswith(str(self.root)):
            raise UnsupportedFileError("잘못된 경로입니다.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

        return StoredFile(
            url=f"{self.public_prefix}/{key}",
            key=key,
            size=len(data),
            content_type=mime,
        )

    def delete(self, key: str) -> bool:
        target = (self.root / key).resolve()
        if not str(target).startswith(str(self.root)) or not target.is_file():
            return False
        target.unlink()
        return True
