"""SafetyScanner 는 오탐/미탐이 곧 제품 신뢰도라 회귀 테스트를 촘촘히 둔다."""

import pytest

from src.domain.services.safety_scanner import SafetyScanner


@pytest.fixture()
def scanner():
    return SafetyScanner()


def categories(findings):
    return {f["category"] for f in findings}


# --------------------------------------------------------------- 탐지되어야 함


@pytest.mark.parametrize(
    "content,expected",
    [
        # 대입 형태가 아닌 '맨몸' 크리덴셜도 잡아야 한다.
        ("실수로 붙여넣은 sk-abcdefghijklmnopqrstuvwxyz1234567890 값", "token"),
        ("ghp_abcdefghijklmnopqrstuvwxyz1234567890AB 를 커밋했다", "token"),
        ("AKIAIOSFODNN7EXAMPLE 키가 노출됨", "token"),
        ("-----BEGIN RSA PRIVATE KEY-----", "token"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456", "token"),
        ("연락처는 010-1234-5678 입니다", "phone"),
        ("담당자 kim.chulsoo@mycompany.co.kr 로 문의", "email"),
        ("서버는 http://192.168.0.14:8080/admin 에서 확인", "internal_url"),
        ("https://db.internal/status 를 확인", "internal_url"),
        # 기술 글에는 http 아닌 스킴이 그대로 붙여넣기 된다.
        ("접속 정보는 redis://10.0.3.14:6379 였다", "internal_url"),
        ("postgres://user:pw@172.20.5.9:5432/app 로 연결", "internal_url"),
        # 스킴 없이 적힌 사설 IP 도 내부 토폴로지를 노출한다.
        ("10.0.3.14:6379 로 붙었더니 timeout", "internal_url"),
    ],
)
def test_detects_sensitive_values(scanner, content, expected):
    assert expected in categories(scanner.scan(content))


@pytest.mark.parametrize(
    "content",
    [
        "api_key = sk-abcdefghijklmnopqrstuvwxyz1234567890",
        "token: ghp_abcdefghijklmnopqrstuvwxyz1234567890AB",
        'AWS_SECRET_KEY="wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY"',
    ],
)
def test_key_value_credentials_are_flagged_high(scanner, content):
    """`key = value` 형태는 secret 으로 분류되며 심각도는 high 다."""
    findings = scanner.scan(content)
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert findings[0]["category"] in {"secret", "token"}


def test_secret_assignment_is_high_severity(scanner):
    findings = scanner.scan('password = "hunter2hunter2"')
    assert findings
    assert findings[0]["severity"] == "high"


# ------------------------------------------------------- 탐지되지 않아야 함


def test_placeholder_email_is_ignored(scanner):
    assert scanner.scan("문의는 hello@example.com 으로") == []


def test_placeholder_secret_is_ignored(scanner):
    assert scanner.scan('api_key = "<your-api-key>"') == []
    assert scanner.scan("api_key = ${OPENAI_API_KEY}") == []


def test_real_email_containing_test_is_not_skipped(scanner):
    """예전 구현은 'test' 가 들어가면 무조건 건너뛰어 실제 주소를 놓쳤다."""
    findings = scanner.scan("latest@mycompany.co.kr 로 보내주세요")
    assert "email" in categories(findings)


def test_plain_numbers_are_not_phone_numbers(scanner):
    """예전 국제번호 정규식은 6자리 이상 숫자를 전부 잡았다."""
    content = "포트 8080 에서 12345678 건을 처리했고 응답 시간은 1234567 ms 였다"
    assert scanner.scan(content) == []


def test_public_url_is_not_internal(scanner):
    assert scanner.scan("https://github.com/anthropics/claude-code 참고") == []


def test_bare_localhost_is_not_flagged(scanner):
    """개발 글에 localhost 는 수없이 나오고 유출 가치도 없다. 스킴이 붙은 경우만 잡는다."""
    assert scanner.scan("localhost 에서 먼저 확인해보세요") == []
    assert scanner.scan("포트 3000 번으로 띄우면 됩니다") == []


def test_public_ip_is_not_flagged(scanner):
    """사설 대역이 아니면 내부 주소가 아니다."""
    assert scanner.scan("8.8.8.8 로 확인했다") == []


# ------------------------------------------------------------------ 위치/중복


def test_location_offsets_point_at_the_match(scanner):
    content = "연락처: 010-1234-5678"
    finding = scanner.scan(content)[0]
    loc = finding["location"]
    line = content.split("\n")[loc["line"] - 1]
    assert line[loc["column"] : loc["end_column"]] == finding["snippet"]


def test_overlapping_matches_are_deduped(scanner):
    """secret 패턴과 token 패턴이 같은 구간에 걸려도 하나만 남는다."""
    findings = scanner.scan("api_key = sk-abcdefghijklmnopqrstuvwxyz1234567890")
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"


def test_findings_are_sorted_by_position(scanner):
    content = "\n".join(
        [
            "https://10.0.0.5/internal",
            "no secrets here",
            "contact: dev@mycompany.co.kr",
        ]
    )
    lines = [f["location"]["line"] for f in scanner.scan(content)]
    assert lines == sorted(lines)


# -------------------------------------------------------------- 마스킹/삭제


def test_mask_uses_offsets_not_string_replace(scanner):
    """같은 값이 두 번 나올 때 지정된 위치만 마스킹되어야 한다."""
    content = "a@mycompany.com 그리고 a@mycompany.com"
    findings = scanner.scan(content)
    assert len(findings) == 2

    masked = scanner.mask_content(content, findings[1])
    assert masked.startswith("a@mycompany.com")  # 첫 번째는 그대로
    assert masked.count("*") == len(findings[1]["snippet"])


def test_remove_finding_only_removes_the_value(scanner):
    content = "토큰은 sk-abcdefghijklmnopqrstuvwxyz1234567890 입니다"
    finding = scanner.scan(content)[0]
    result = scanner.remove_finding(content, finding)
    assert result == "토큰은  입니다"
    assert "sk-" not in result


def test_mask_returns_original_when_offset_is_stale(scanner):
    finding = {"snippet": "sk-nolongerhere", "location": {"line": 1, "column": 0, "end_column": 15}}
    content = "완전히 다른 내용"
    assert scanner.mask_content(content, finding) == content


def test_empty_content(scanner):
    assert scanner.scan("") == []
