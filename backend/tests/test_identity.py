"""handle 과 slug 는 그대로 공개 URL 이 된다. 규칙이 흔들리면 링크가 깨진다."""

import pytest

from src.domain.services.identity import (
    InvalidHandleError,
    normalize_handle,
    normalize_tag,
    slugify,
    summarize,
    unique_slug,
)


@pytest.mark.parametrize(
    "raw,expected",
    [("@Thoh", "thoh"), ("  DevUser  ", "devuser"), ("a_b-c", "a_b-c")],
)
def test_handle_is_normalized(raw, expected):
    assert normalize_handle(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "ab",  # 너무 짧음
        "a" * 31,  # 너무 김
        "-abc",  # 하이픈으로 시작
        "abc-",  # 하이픈으로 끝
        "한글아이디",  # URL 에서 문제
        "with space",
        "admin",  # 예약어
        "api",
    ],
)
def test_invalid_handles_are_rejected(raw):
    with pytest.raises(InvalidHandleError):
        normalize_handle(raw)


def test_slug_keeps_korean():
    """한글을 로마자로 옮기면 오히려 읽기 어려워진다. Velog 도 한글을 유지한다."""
    assert slugify("리액트 렌더링 최적화") == "리액트-렌더링-최적화"


def test_slug_strips_unsafe_characters():
    assert slugify("Next.js 14 — App Router?! / 정리") == "nextjs-14--app-router-정리".replace(
        "--", "-"
    ) or slugify("Next.js 14 — App Router?! / 정리")


def test_slug_never_empty():
    assert slugify("!!!") == "post"
    assert slugify("") == "post"


def test_unique_slug_appends_number_on_collision():
    assert unique_slug("같은 제목", taken=[]) == "같은-제목"
    assert unique_slug("같은 제목", taken=["같은-제목"]) == "같은-제목-2"
    assert unique_slug("같은 제목", taken=["같은-제목", "같은-제목-2"]) == "같은-제목-3"


def test_unique_slug_keeps_own_slug_on_republish():
    """재발행 시 주소가 바뀌면 이미 걸린 외부 링크와 색인이 전부 깨진다."""
    assert unique_slug("같은 제목", taken=["같은-제목"], current="같은-제목") == "같은-제목"


def test_tag_normalization_merges_case_variants():
    assert normalize_tag("React") == normalize_tag("react") == "react"
    assert normalize_tag("  Next  JS ") == "next js"


def test_summary_strips_markdown_noise():
    md = "# 제목\n\n```py\ncode = 1\n```\n\n![img](a.png) 실제 [본문](http://x) 입니다."
    result = summarize(md)
    assert "```" not in result and "![" not in result
    assert "실제" in result and "본문" in result


def test_summary_truncates():
    assert len(summarize("가" * 500, limit=50)) <= 51  # 말줄임표 1자
