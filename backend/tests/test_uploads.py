"""업로드: 형식 판별, 리사이징, 정리."""

import io
import struct
import zlib

import pytest

from src.application.use_cases.upload.upload_image import DeleteUploadUseCase, UploadImageUseCase
from src.domain.services.images import UnsupportedFileError, resize_variants, sniff_image
from src.ports.output.services.storage_service import StorageService


def png_bytes(width: int = 8, height: int = 8) -> bytes:
    """진짜 PNG. 매직바이트 검사와 Pillow 디코딩을 모두 통과해야 한다."""
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class MemoryStorage(StorageService):
    """디스크·네트워크 없이 포트 계약만 검증한다."""

    def __init__(self):
        self.objects = {}

    def put(self, key, data, content_type):
        self.objects[key] = (data, content_type)
        return self.url_for(key)

    def delete(self, key):
        return self.objects.pop(key, None) is not None

    def url_for(self, key):
        return f"/uploads/{key}"

    def key_from_url(self, url):
        return url[len("/uploads/"):] if url.startswith("/uploads/") else ""


# ------------------------------------------------------------------ 형식 판별


def test_png_은_확장자와_무관하게_png_로_판별된다():
    assert sniff_image(png_bytes()) == ("png", "image/png")


def test_jpeg_매직바이트():
    assert sniff_image(b"\xff\xd8\xff\xe0rest") == ("jpg", "image/jpeg")


def test_webp_는_riff_와_webp_를_모두_봐야_한다():
    assert sniff_image(b"RIFF\x00\x00\x00\x00WEBPmore") == ("webp", "image/webp")
    with pytest.raises(UnsupportedFileError):
        # RIFF 지만 WEBP 가 아니면(예: WAV) 거절해야 한다.
        sniff_image(b"RIFF\x00\x00\x00\x00WAVEfmt ")


def test_확장자만_이미지인_스크립트는_거절된다():
    with pytest.raises(UnsupportedFileError):
        sniff_image(b"<?php system($_GET[0]); ?>")


def test_html_은_거절된다():
    # image/png 라고 주장하는 HTML 을 통과시키면 저장형 XSS 가 된다.
    with pytest.raises(UnsupportedFileError):
        sniff_image(b"<html><script>alert(1)</script></html>")


# -------------------------------------------------------------------- 리사이징


def test_원본보다_큰_변형은_만들지_않는다():
    # 8px 이미지에 1200w/400w 를 만들면 화질만 나빠지고 용량만 는다.
    assert resize_variants(png_bytes(8, 8), "png") == []


def test_큰_이미지는_변형이_생긴다():
    variants = resize_variants(png_bytes(1600, 900), "png")
    names = {name for name, _, _ in variants}
    # 투명도가 없는 원본은 JPEG 로 낸다. PNG 로 두면 사진에서 용량이 몇 배가 된다.
    assert names == {"w1200.jpg", "w400.jpg"}
    for _, blob, mime in variants:
        assert blob and mime == "image/jpeg"


def test_투명한_이미지는_png_로_유지된다():
    """알파를 JPEG 로 바꾸면 투명한 부분이 검게 칠해진다."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGBA", (1600, 900), (255, 0, 0, 128)).save(buffer, "PNG")

    names = {name for name, _, _ in resize_variants(buffer.getvalue(), "png")}
    assert names == {"w1200.png", "w400.png"}


def test_변형은_가로세로_비율을_유지한다():
    from PIL import Image

    variants = resize_variants(png_bytes(1600, 900), "png")
    blob = next(b for name, b, _ in variants if name.startswith("w1200"))
    with Image.open(io.BytesIO(blob)) as resized:
        assert resized.size == (1200, 675)  # 1600:900 == 1200:675


def test_gif_는_건드리지_않는다():
    # 애니메이션이 첫 프레임만 남고 정지 이미지가 되는 것을 막는다.
    assert resize_variants(b"GIF89a" + b"\x00" * 100, "gif") == []


def test_손상된_파일은_예외_대신_빈_목록():
    # 원본은 이미 판별을 통과했다. 변형 실패로 업로드 전체를 깨지 않는다.
    assert resize_variants(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, "png") == []


# ------------------------------------------------------------------ 업로드 흐름


def test_업로드는_원본과_변형을_모두_저장한다():
    storage = MemoryStorage()
    result = UploadImageUseCase(storage).execute(png_bytes(1600, 900), prefix="posts")

    assert result.variants["original"].endswith(".png")
    assert "w1200" in result.variants and "w400" in result.variants
    # 화면에 쓰는 기본 주소는 원본이 아니라 리사이즈본이어야 한다.
    assert result.url == result.variants["w1200"]
    assert len(storage.objects) == 3


def test_파일명은_클라이언트가_준_것을_쓰지_않는다():
    storage = MemoryStorage()
    result = UploadImageUseCase(storage).execute(png_bytes(), prefix="posts")
    assert result.key.startswith("posts/")
    assert ".." not in result.key


def test_prefix_의_경로문자는_걸러진다():
    storage = MemoryStorage()
    result = UploadImageUseCase(storage).execute(png_bytes(), prefix="../../etc")
    assert ".." not in result.key and "/etc" not in result.key


def test_용량_초과는_거절된다(monkeypatch):
    from src.infrastructure.config import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(UnsupportedFileError):
        UploadImageUseCase(MemoryStorage()).execute(png_bytes())


def test_빈_파일은_거절된다():
    with pytest.raises(UnsupportedFileError):
        UploadImageUseCase(MemoryStorage()).execute(b"")


# ---------------------------------------------------------------------- 정리


def test_삭제는_원본과_변형을_함께_지운다():
    storage = MemoryStorage()
    result = UploadImageUseCase(storage).execute(png_bytes(1600, 900), prefix="posts")
    assert len(storage.objects) == 3

    DeleteUploadUseCase(storage).execute(result.url)  # 변형 주소로 지워도
    assert storage.objects == {}  # 원본까지 사라져야 한다


def test_외부_주소는_지우려_하지_않는다():
    storage = MemoryStorage()
    storage.objects["keep"] = (b"x", "image/png")
    assert DeleteUploadUseCase(storage).execute("https://example.com/a.png") == 0
    assert storage.objects  # 남의 저장소 것을 건드리지 않는다


def test_없는_주소_삭제는_조용히_0():
    assert DeleteUploadUseCase(MemoryStorage()).execute(None) == 0
    assert DeleteUploadUseCase(MemoryStorage()).execute("/uploads/posts/nope.png") == 0
