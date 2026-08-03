"""저장소 선택.

한 번 만든 인스턴스를 재사용한다. S3 클라이언트는 세션·커넥션 풀을 들고 있어서
요청마다 새로 만들면 소켓이 계속 새로 열린다.
"""

from functools import lru_cache

from src.infrastructure.config.settings import settings
from src.ports.output.services.storage_service import StorageService


@lru_cache(maxsize=1)
def get_storage() -> StorageService:
    if settings.STORAGE_BACKEND == "s3":
        from src.infrastructure.external.storage.s3_storage import S3StorageService

        return S3StorageService()

    from src.infrastructure.external.storage.local_storage import LocalStorageService

    return LocalStorageService()


__all__ = ["get_storage", "StorageService"]
