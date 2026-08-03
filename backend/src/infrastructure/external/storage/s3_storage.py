"""S3(호환) 저장소.

운영 기본값. MinIO·R2 처럼 S3 API 를 따르는 곳이면 STORAGE_S3_ENDPOINT 만 지정하면 된다.

공개 주소는 두 갈래다.
- CDN 앞단이 있으면 STORAGE_PUBLIC_BASE_URL 을 쓴다 (권장. 캐시가 붙는다).
- 없으면 버킷 기본 주소로 만든다. 이때 버킷이 공개 읽기여야 한다.
Presigned URL 을 쓰지 않는 이유: 글에 박히는 주소라 만료되면 과거 글의 이미지가 전부 깨진다.
"""

from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.infrastructure.config.settings import settings
from src.ports.output.services.storage_service import StorageService


class S3StorageService(StorageService):
    def __init__(self, client=None, bucket: Optional[str] = None):
        self.bucket = bucket or settings.STORAGE_S3_BUCKET
        if not self.bucket:
            raise ValueError("STORAGE_BACKEND=s3 인데 STORAGE_S3_BUCKET 이 비어 있습니다.")

        self.client = client or boto3.client(
            "s3",
            endpoint_url=settings.STORAGE_S3_ENDPOINT or None,
            region_name=settings.STORAGE_S3_REGION or None,
            aws_access_key_id=settings.STORAGE_S3_ACCESS_KEY or None,
            aws_secret_access_key=settings.STORAGE_S3_SECRET_KEY or None,
            # 재시도를 표준 모드로. 기본 legacy 모드는 스로틀링 응답을 제대로 못 읽는다.
            config=Config(retries={"max_attempts": 3, "mode": "standard"}),
        )
        self.public_base = (settings.STORAGE_PUBLIC_BASE_URL or "").rstrip("/")

    def put(self, key: str, data: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            # 이미지는 내용이 바뀌지 않는다(키가 무작위라 덮어쓰지 않음). 길게 캐시한다.
            CacheControl="public, max-age=31536000, immutable",
        )
        return self.url_for(key)

    def delete(self, key: str) -> bool:
        if not key:
            return False
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            # 이미 없는 경우를 포함해 실패는 조용히 넘긴다. 정리 실패로 본 요청을 깨지 않는다.
            return False

    def url_for(self, key: str) -> str:
        key = key.lstrip("/")
        if self.public_base:
            return f"{self.public_base}/{key}"
        if settings.STORAGE_S3_ENDPOINT:
            return f"{settings.STORAGE_S3_ENDPOINT.rstrip('/')}/{self.bucket}/{key}"
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    def key_from_url(self, url: str) -> str:
        for base in (self.public_base, self.url_for("").rstrip("/")):
            prefix = f"{base}/"
            if base and url.startswith(prefix):
                return url[len(prefix):]
        return ""
