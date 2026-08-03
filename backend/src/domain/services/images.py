"""이미지 판별과 리사이징.

저장소(로컬/S3) 와 무관한 규칙이라 도메인에 둔다.

판별을 매직 넘버로 하는 이유: 확장자와 Content-Type 은 클라이언트가 마음대로 보낸다.
image/png 라고 주장하는 HTML 을 그대로 저장하면 저장형 XSS 가 된다.
"""

import io
from typing import List, Optional, Tuple

# 매직 넘버 → (확장자, 정규화된 MIME)
_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"GIF87a", "gif", "image/gif"),
    (b"GIF89a", "gif", "image/gif"),
]

# 피드 카드와 본문에서 실제로 쓰는 폭. 원본은 따로 보관한다.
VARIANTS: List[Tuple[str, int]] = [("w1200", 1200), ("w400", 400)]


class UnsupportedFileError(ValueError):
    """허용하지 않는 파일 형식"""


def sniff_image(data: bytes) -> Tuple[str, str]:
    """바이트를 보고 이미지 형식을 판별한다. 아니면 예외."""
    for signature, ext, mime in _SIGNATURES:
        if data.startswith(signature):
            return ext, mime

    # WebP: "RIFF....WEBP"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"

    raise UnsupportedFileError("PNG, JPEG, GIF, WebP 이미지만 올릴 수 있습니다.")


def _pillow():
    """Pillow 를 지연 임포트한다. 없으면 리사이징만 건너뛰고 업로드는 계속되게."""
    try:
        from PIL import Image  # noqa: PLC0415

        return Image
    except ImportError:
        return None


def resize_variants(data: bytes, ext: str) -> List[Tuple[str, bytes, str]]:
    """(이름, 바이트, MIME) 목록을 만든다. 원본은 포함하지 않는다.

    - 애니메이션 GIF 는 건드리지 않는다. 리사이즈하면 첫 프레임만 남아 정지 이미지가 된다.
    - 원본보다 큰 변형은 만들지 않는다. 늘려 봐야 화질만 나빠지고 용량만 는다.
    - Pillow 가 없거나 디코딩에 실패하면 빈 목록. 업로드 자체를 실패시키지는 않는다.
    """
    Image = _pillow()
    if Image is None or ext == "gif":
        return []

    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            if getattr(source, "n_frames", 1) > 1:
                return []

            has_alpha = source.mode in ("RGBA", "LA", "P")
            out_ext, out_mime = ("png", "image/png") if has_alpha else ("jpg", "image/jpeg")
            base = source.convert("RGBA" if has_alpha else "RGB")

            results: List[Tuple[str, bytes, str]] = []
            for name, width in VARIANTS:
                if base.width <= width:
                    continue
                height = max(1, round(base.height * width / base.width))
                buffer = io.BytesIO()
                resized = base.resize((width, height), Image.LANCZOS)
                if out_ext == "jpg":
                    resized.save(buffer, "JPEG", quality=82, optimize=True, progressive=True)
                else:
                    resized.save(buffer, "PNG", optimize=True)
                results.append((f"{name}.{out_ext}", buffer.getvalue(), out_mime))
            return results
    except Exception:
        # 손상된 파일이나 Pillow 가 못 여는 형식 — 원본만 저장하고 넘어간다.
        return []


def dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    """(width, height). 못 읽으면 None."""
    Image = _pillow()
    if Image is None:
        return None
    try:
        with Image.open(io.BytesIO(data)) as source:
            return source.size
    except Exception:
        return None
