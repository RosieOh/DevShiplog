"""S3 호환 오브젝트 저장소 (MinIO 기본).

MinIO 를 기본으로 쓴다. AWS S3 와 API 가 같아서 코드는 한 벌이면 되고,
개발·CI 에서 컨테이너로 띄울 수 있어 "로컬은 디스크, 운영은 S3" 같은 갈라짐이 없다.
운영에서 AWS 로 옮기고 싶으면 STORAGE_S3_ENDPOINT 만 비우면 된다.

공개 주소는 두 갈래다.
- STORAGE_PUBLIC_BASE_URL 이 있으면 그걸 쓴다. 컨테이너 안에서는 http://minio:9000 으로
  붙지만 브라우저는 그 호스트명을 모르므로, 개발에서도 이 값이 사실상 필수다.
- 없으면 엔드포인트+버킷으로 만든다.
Presigned URL 을 쓰지 않는 이유: 글 본문에 박히는 주소라 만료되면 과거 글의 이미지가 전부 깨진다.
"""

import logging
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.infrastructure.config.settings import settings
from src.ports.output.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# 버킷 전체를 익명 읽기로 여는 정책. 글에 박히는 이미지라 누구나 읽을 수 있어야 한다.
# 쓰기는 열지 않는다 — 자격증명을 가진 백엔드만 올린다.
_PUBLIC_READ_POLICY = """{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": ["*"]},
    "Action": ["s3:GetObject"],
    "Resource": ["arn:aws:s3:::%s/*"]
  }]
}"""


class S3StorageService(StorageService):
    def __init__(self, client=None, bucket: Optional[str] = None):
        self.bucket = bucket or settings.STORAGE_S3_BUCKET
        if not self.bucket:
            raise ValueError("STORAGE_BACKEND=s3 인데 STORAGE_S3_BUCKET 이 비어 있습니다.")

        self.endpoint = (settings.STORAGE_S3_ENDPOINT or "").rstrip("/")
        self.client = client or boto3.client(
            "s3",
            endpoint_url=self.endpoint or None,
            region_name=settings.STORAGE_S3_REGION or None,
            aws_access_key_id=settings.STORAGE_S3_ACCESS_KEY or None,
            aws_secret_access_key=settings.STORAGE_S3_SECRET_KEY or None,
            config=Config(
                # 재시도를 표준 모드로. 기본 legacy 모드는 스로틀링 응답을 제대로 못 읽는다.
                retries={"max_attempts": 3, "mode": "standard"},
                # MinIO 는 경로 방식 주소만 받는다. 기본값(가상 호스트 방식)이면
                # bucket.minio:9000 으로 붙으려 해서 DNS 부터 실패한다.
                s3={"addressing_style": "path"} if self.endpoint else {},
            ),
        )
        self.public_base = (settings.STORAGE_PUBLIC_BASE_URL or "").rstrip("/")

    def ensure_bucket(self) -> None:
        """버킷이 없으면 만들고 공개 읽기로 연다.

        MinIO 는 빈 상태로 뜨므로 누군가는 버킷을 만들어야 한다. 기동할 때 여기서
        처리하면 개발자가 콘솔에 들어가 손으로 만들 필요가 없고, CI 도 그냥 돈다.
        이미 있으면 아무 일도 하지 않는다.
        """
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in ("404", "NoSuchBucket"):
                # 403 이면 남의 버킷이거나 자격증명이 틀렸다. 조용히 덮지 않는다.
                raise

        self.client.create_bucket(Bucket=self.bucket)
        self.client.put_bucket_policy(
            Bucket=self.bucket, Policy=_PUBLIC_READ_POLICY % self.bucket
        )
        logger.info("오브젝트 저장소 버킷 생성: %s", self.bucket)

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
        if self.endpoint:
            return f"{self.endpoint}/{self.bucket}/{key}"
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    def key_from_url(self, url: str) -> str:
        # 공개 주소가 도중에 바뀌어도(예: CDN 을 나중에 붙임) 옛 주소로 저장된 것을
        # 지울 수 있어야 하므로 후보를 모두 본다.
        candidates = [self.public_base]
        if self.endpoint:
            candidates.append(f"{self.endpoint}/{self.bucket}")
        candidates.append(f"https://{self.bucket}.s3.amazonaws.com")

        for base in candidates:
            prefix = f"{base}/"
            if base and url.startswith(prefix):
                return url[len(prefix):]
        return ""
