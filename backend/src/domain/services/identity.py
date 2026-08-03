"""블로그 신원(handle)과 글 주소(slug) 규칙.

URL 이 `devshiplog.com/@handle/slug` 이므로 이 두 값이 곧 공개 주소다.
한 번 정해지면 외부 링크·검색 색인이 걸리므로 규칙을 도메인에 고정해 둔다.
"""

import re
import unicodedata
from typing import Iterable, Optional

HANDLE_MIN = 3
HANDLE_MAX = 30
_HANDLE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{1,28}[a-z0-9])$")

# `@` 접두사 덕분에 앱 라우트(/dashboard 등)와는 구조적으로 충돌하지 않는다.
# 다만 오해를 부르거나 사칭에 쓰일 수 있는 이름은 막는다.
RESERVED_HANDLES = frozenset(
    {
        "admin", "administrator", "root", "system", "support", "help", "staff",
        "official", "devshiplog", "api", "www", "mail", "static", "assets",
        "about", "terms", "privacy", "settings", "login", "logout", "signup",
        "me", "you", "null", "undefined", "anonymous", "deleted",
    }
)

SLUG_MAX = 80


class InvalidHandleError(ValueError):
    """사용할 수 없는 handle"""


def normalize_handle(raw: str) -> str:
    """handle 을 소문자로 정규화하고 규칙을 검사한다."""
    handle = (raw or "").strip().lstrip("@").lower()

    if not (HANDLE_MIN <= len(handle) <= HANDLE_MAX):
        raise InvalidHandleError(f"아이디는 {HANDLE_MIN}~{HANDLE_MAX}자여야 합니다.")
    if not _HANDLE_RE.match(handle):
        raise InvalidHandleError(
            "아이디는 영문 소문자·숫자로 시작하고 끝나야 하며, 중간에 - 와 _ 만 쓸 수 있습니다."
        )
    if handle in RESERVED_HANDLES:
        raise InvalidHandleError("이미 예약된 아이디입니다.")
    return handle


def slugify(title: str) -> str:
    """제목을 URL 조각으로 바꾼다.

    한글을 그대로 살린다. Velog 처럼 `/@handle/리액트-렌더링-최적화` 가 되며,
    브라우저가 알아서 퍼센트 인코딩한다. 로마자로 옮기면 오히려 읽기 어려워진다.
    """
    text = unicodedata.normalize("NFC", title or "").strip().lower()
    # 공백류 → 하이픈
    text = re.sub(r"\s+", "-", text)
    # 링크에서 문제를 일으키는 문자 제거 (한글/영문/숫자/하이픈만 남긴다)
    text = re.sub(r"[^\w가-힣-]", "", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:SLUG_MAX] or "post"


def unique_slug(title: str, taken: Iterable[str], current: Optional[str] = None) -> str:
    """같은 사용자 안에서 겹치지 않는 slug 를 만든다.

    current 를 넘기면 자기 자신은 충돌로 치지 않는다(재발행 시 주소 유지).
    """
    base = slugify(title)
    taken = {s for s in taken if s != current}
    if base not in taken:
        return base

    for n in range(2, 1000):
        candidate = f"{base}-{n}"
        if len(candidate) > SLUG_MAX:
            candidate = f"{base[: SLUG_MAX - len(str(n)) - 1]}-{n}"
        if candidate not in taken:
            return candidate

    raise ValueError("사용 가능한 주소를 만들지 못했습니다.")


def normalize_tag(raw: str) -> str:
    """태그 표기를 통일한다. 대소문자만 다른 태그가 갈라지지 않도록."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", raw or "").strip()).lower()[:40]


def summarize(markdown: str, limit: int = 160) -> str:
    """목록·검색결과·OG 설명에 쓸 요약을 본문에서 뽑는다."""
    text = markdown or ""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # 코드블록
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # 이미지
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # 링크 → 텍스트
    text = re.sub(r"[#>*_`~|-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip() + ("…" if len(text) > limit else "")
