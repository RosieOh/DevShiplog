"""MinIO/S3 저장소 어댑터.

실제 MinIO 없이 돌아야 하므로 boto3 클라이언트를 가짜로 끼운다. 여기서 검증하는 건
"우리가 boto3 를 올바르게 부르는가" 와 "주소를 올바르게 만드는가" 다.
"""

import pytest
from botocore.exceptions import ClientError

from src.infrastructure.config import settings as settings_module
from src.infrastructure.external.storage.s3_storage import S3StorageService


class FakeS3:
    def __init__(self, existing_buckets=()):
        self.buckets = set(existing_buckets)
        self.objects = {}
        self.policies = {}

    def head_bucket(self, Bucket):
        if Bucket not in self.buckets:
            raise ClientError({"Error": {"Code": "404"}}, "HeadBucket")

    def create_bucket(self, Bucket):
        self.buckets.add(Bucket)

    def put_bucket_policy(self, Bucket, Policy):
        self.policies[Bucket] = Policy

    def put_object(self, Bucket, Key, Body, ContentType, CacheControl):
        self.objects[(Bucket, Key)] = (Body, ContentType, CacheControl)

    def delete_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "DeleteObject")
        del self.objects[(Bucket, Key)]


@pytest.fixture
def minio(monkeypatch):
    """MinIO 를 가리키는 설정 + 가짜 클라이언트."""
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_BUCKET", "devshiplog")
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(
        settings_module.settings, "STORAGE_PUBLIC_BASE_URL", "http://localhost:9000/devshiplog"
    )
    fake = FakeS3()
    return S3StorageService(client=fake, bucket="devshiplog"), fake


def test_버킷이_없으면_만들고_공개읽기로_연다(minio):
    storage, fake = minio
    storage.ensure_bucket()

    assert "devshiplog" in fake.buckets
    policy = fake.policies["devshiplog"]
    assert "s3:GetObject" in policy
    # 쓰기는 열지 않는다. 자격증명을 가진 백엔드만 올려야 한다.
    assert "s3:PutObject" not in policy


def test_이미_있는_버킷은_건드리지_않는다(minio, monkeypatch):
    storage, fake = minio
    fake.buckets.add("devshiplog")
    storage.ensure_bucket()
    assert fake.policies == {}  # 정책을 덮어쓰지 않는다


def test_권한_오류는_삼키지_않는다(minio):
    """403 이면 남의 버킷이거나 자격증명이 틀렸다. 조용히 덮으면 안 된다."""
    storage, fake = minio

    def forbidden(Bucket):
        raise ClientError({"Error": {"Code": "403"}}, "HeadBucket")

    fake.head_bucket = forbidden
    with pytest.raises(ClientError):
        storage.ensure_bucket()


def test_업로드는_공개_주소를_돌려준다(minio):
    storage, fake = minio
    url = storage.put("posts/abc.png", b"data", "image/png")

    assert url == "http://localhost:9000/devshiplog/posts/abc.png"
    body, content_type, cache = fake.objects[("devshiplog", "posts/abc.png")]
    assert body == b"data" and content_type == "image/png"
    # 키가 무작위라 내용이 바뀌지 않는다. 길게 캐시해도 안전하다.
    assert "immutable" in cache


def test_내부_엔드포인트가_아니라_공개_주소를_쓴다(minio):
    """컨테이너 안에서는 minio:9000 으로 붙지만 브라우저는 그 호스트를 모른다."""
    storage, _ = minio
    assert "minio:9000" not in storage.url_for("posts/abc.png")


def test_공개_주소에서_key_를_되짚는다(minio):
    storage, _ = minio
    url = storage.url_for("posts/abc.png")
    assert storage.key_from_url(url) == "posts/abc.png"


def test_옛_엔드포인트_주소도_되짚는다(minio):
    """나중에 CDN 을 붙여도 그전에 저장된 주소를 지울 수 있어야 한다."""
    storage, _ = minio
    assert storage.key_from_url("http://minio:9000/devshiplog/posts/old.png") == "posts/old.png"


def test_남의_주소는_key_가_없다(minio):
    storage, _ = minio
    assert storage.key_from_url("https://example.com/a.png") == ""


def test_삭제_실패는_예외가_아니라_False(minio):
    storage, _ = minio
    assert storage.delete("posts/nope.png") is False
    assert storage.delete("") is False


def test_삭제(minio):
    storage, fake = minio
    storage.put("posts/abc.png", b"data", "image/png")
    assert storage.delete("posts/abc.png") is True
    assert fake.objects == {}


def test_공개_주소가_없으면_엔드포인트로_만든다(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(settings_module.settings, "STORAGE_PUBLIC_BASE_URL", "")
    storage = S3StorageService(client=FakeS3(), bucket="devshiplog")
    assert storage.url_for("a.png") == "http://minio:9000/devshiplog/a.png"


def test_엔드포인트가_없으면_aws_주소(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_ENDPOINT", "")
    monkeypatch.setattr(settings_module.settings, "STORAGE_PUBLIC_BASE_URL", "")
    storage = S3StorageService(client=FakeS3(), bucket="devshiplog")
    assert storage.url_for("a.png") == "https://devshiplog.s3.amazonaws.com/a.png"


def test_버킷이_비면_기동하지_않는다(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_BUCKET", "")
    with pytest.raises(ValueError):
        S3StorageService(client=FakeS3())
