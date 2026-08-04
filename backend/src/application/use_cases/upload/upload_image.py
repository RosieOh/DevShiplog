"""이미지 업로드.

판별 → 파생본 생성 → 저장 순서. 저장소가 로컬이든 S3 든 이 순서는 같다.
"""

import secrets
from typing import Optional

from src.domain.services.images import UnsupportedFileError, resize_variants, sniff_image
from src.infrastructure.config.settings import settings
from src.ports.output.services.storage_service import StorageService, StoredFile


class UploadImageUseCase:
    def __init__(self, storage: StorageService):
        self.storage = storage

    def execute(self, data: bytes, prefix: str = "") -> StoredFile:
        if not data:
            raise UnsupportedFileError("빈 파일입니다.")
        if len(data) > settings.MAX_UPLOAD_BYTES:
            limit_mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
            raise UnsupportedFileError(f"파일이 너무 큽니다 (최대 {limit_mb}MB).")

        ext, mime = sniff_image(data)

        # 파일명은 클라이언트가 준 것을 쓰지 않는다. `../../etc/passwd` 같은 값이 온다.
        safe_prefix = "".join(c for c in prefix if c.isalnum() or c in "-_")
        stem = secrets.token_urlsafe(16)
        base = f"{safe_prefix}/{stem}" if safe_prefix else stem

        original_key = f"{base}.{ext}"
        original_url = self.storage.put(original_key, data, mime)

        variants = {}
        for name, blob, blob_mime in resize_variants(data, ext):
            variant_key = f"{base}.{name}"
            # 파생본 저장이 실패해도 원본은 이미 올라갔다. 업로드 자체를 깨지 않는다.
            try:
                variants[name.split(".")[0]] = self.storage.put(variant_key, blob, blob_mime)
            except Exception:
                continue

        return StoredFile(
            # 화면에 쓰는 기본 주소는 리사이즈본. 원본은 필요할 때만 꺼낸다.
            url=variants.get("w1200", original_url),
            key=original_key,
            size=len(data),
            content_type=mime,
            variants={"original": original_url, **variants},
        )


class DeleteUploadUseCase:
    """공개 URL 로 원본과 파생본을 함께 지운다.

    URL 하나만 DB 에 남기므로, 파생본 키는 원본 키에서 규칙으로 되짚는다.
    """

    def __init__(self, storage: StorageService):
        self.storage = storage

    def execute(self, url: Optional[str]) -> int:
        if not url:
            return 0
        key = self.storage.key_from_url(url)
        if not key:
            # 외부 주소(사용자가 직접 넣은 https 이미지)는 우리가 지울 것이 없다.
            return 0

        removed = 0
        # 저장된 URL 이 파생본일 수 있으므로 확장자 앞 stem 을 기준으로 형제들을 지운다.
        stem = key.rsplit(".", 1)[0]
        for suffix in (".w1200", ".w400"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        for candidate in (
            key,
            f"{stem}.png", f"{stem}.jpg", f"{stem}.gif", f"{stem}.webp",
            f"{stem}.w1200.jpg", f"{stem}.w1200.png",
            f"{stem}.w400.jpg", f"{stem}.w400.png",
        ):
            if self.storage.delete(candidate):
                removed += 1
        return removed
