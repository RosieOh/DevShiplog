"""AWS S3 경로 검증.

MinIO 로만 확인하면 "엔드포인트를 비웠을 때" 경로는 한 번도 안 돈다.
그쪽은 주소 형식(가상 호스트 방식)과 리전 처리가 달라서, 실제로 배포하는 날
처음 실행되는 코드가 된다.

moto 로 AWS S3 를 흉내 내 그 경로를 돌린다. 진짜 AWS 는 아니지만
boto3 호출 규약과 응답 형태는 같으므로, 우리가 API 를 잘못 쓰는 것은 잡힌다.
"""

import boto3
import pytest
from moto import mock_aws

from src.application.use_cases.upload.upload_image import DeleteUploadUseCase, UploadImageUseCase
from src.infrastructure.config import settings as settings_module
from src.infrastructure.external.storage.s3_storage import S3StorageService
from tests.test_uploads import png_bytes

BUCKET = "devshiplog-prod"
REGION = "ap-northeast-2"


@pytest.fixture
def aws(monkeypatch):
    """엔드포인트를 비운 = AWS S3 를 쓰는 설정."""
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_BUCKET", BUCKET)
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_REGION", REGION)
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_ENDPOINT", "")
    monkeypatch.setattr(settings_module.settings, "STORAGE_PUBLIC_BASE_URL", "")
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_ACCESS_KEY", "testing")
    monkeypatch.setattr(settings_module.settings, "STORAGE_S3_SECRET_KEY", "testing")

    with mock_aws():
        yield S3StorageService()


def test_버킷을_만들고_공개읽기로_연다(aws):
    aws.ensure_bucket()

    client = boto3.client("s3", region_name=REGION)
    assert BUCKET in [b["Name"] for b in client.list_buckets()["Buckets"]]

    policy = client.get_bucket_policy(Bucket=BUCKET)["Policy"]
    assert "s3:GetObject" in policy
    # 쓰기는 열지 않는다. 자격증명을 가진 백엔드만 올려야 한다.
    assert "s3:PutObject" not in policy


def test_이미_있는_버킷은_정책을_덮지_않는다(aws):
    aws.ensure_bucket()
    client = boto3.client("s3", region_name=REGION)
    client.put_bucket_policy(
        Bucket=BUCKET,
        Policy='{"Version":"2012-10-17","Statement":[{"Sid":"custom","Effect":"Allow",'
        '"Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::%s/*"}]}' % BUCKET,
    )

    aws.ensure_bucket()  # 두 번째 호출
    assert "custom" in client.get_bucket_policy(Bucket=BUCKET)["Policy"]


def test_업로드가_aws_주소를_돌려준다(aws):
    aws.ensure_bucket()
    url = aws.put("posts/abc.png", b"data", "image/png")

    # 엔드포인트가 없으면 가상 호스트 방식 주소여야 한다.
    assert url == f"https://{BUCKET}.s3.amazonaws.com/posts/abc.png"
    assert aws.key_from_url(url) == "posts/abc.png"


def test_객체가_실제로_올라가고_메타데이터가_붙는다(aws):
    aws.ensure_bucket()
    aws.put("posts/abc.png", b"\x89PNG", "image/png")

    obj = boto3.client("s3", region_name=REGION).get_object(Bucket=BUCKET, Key="posts/abc.png")
    assert obj["Body"].read() == b"\x89PNG"
    assert obj["ContentType"] == "image/png"
    # 키가 무작위라 내용이 바뀌지 않는다. 길게 캐시해도 안전하다.
    assert "immutable" in obj["CacheControl"]


def test_업로드_유스케이스가_aws_에서도_동일하게_돈다(aws):
    """리사이징·변형 저장·기본 주소 선택이 저장소에 의존하지 않아야 한다."""
    aws.ensure_bucket()
    result = UploadImageUseCase(aws).execute(png_bytes(1600, 900), prefix="posts")

    assert set(result.variants) == {"original", "w1200", "w400"}
    assert result.url == result.variants["w1200"]
    assert all(u.startswith(f"https://{BUCKET}.s3.amazonaws.com/") for u in result.variants.values())

    keys = [
        o["Key"]
        for o in boto3.client("s3", region_name=REGION).list_objects_v2(Bucket=BUCKET)["Contents"]
    ]
    assert len(keys) == 3


def test_삭제도_원본과_변형을_함께_지운다(aws):
    aws.ensure_bucket()
    result = UploadImageUseCase(aws).execute(png_bytes(1600, 900), prefix="posts")

    DeleteUploadUseCase(aws).execute(result.url)

    listing = boto3.client("s3", region_name=REGION).list_objects_v2(Bucket=BUCKET)
    assert listing.get("KeyCount", 0) == 0


def test_없는_키_삭제는_예외가_아니다(aws):
    aws.ensure_bucket()
    assert aws.delete("posts/nope.png") is True  # S3 는 없는 키 삭제도 성공으로 답한다


def test_CDN_을_붙이면_그_주소를_쓴다(aws, monkeypatch):
    monkeypatch.setattr(
        settings_module.settings, "STORAGE_PUBLIC_BASE_URL", "https://cdn.devshiplog.com"
    )
    storage = S3StorageService()
    storage.ensure_bucket()

    url = storage.put("posts/abc.png", b"data", "image/png")
    assert url == "https://cdn.devshiplog.com/posts/abc.png"
    # CDN 을 나중에 붙여도 그전에 저장된 버킷 주소를 지울 수 있어야 한다.
    assert storage.key_from_url(f"https://{BUCKET}.s3.amazonaws.com/posts/old.png") == "posts/old.png"
