"""민감정보 탐지 도메인 서비스.

설계 원칙
- 오탐(false positive)을 줄이는 쪽에 무게를 둔다. 글쓴이가 매번 무시해야 하는
  경고가 쌓이면 검사 자체를 신뢰하지 않게 된다.
- 다만 크리덴셜(token/secret)은 놓치는 비용이 훨씬 크므로 넓게 잡는다.
- 위치는 (line, column, end_column) 오프셋으로 정확히 기록한다. 마스킹은
  문자열 replace 가 아니라 이 오프셋으로 수행해야 같은 값이 여러 번 나올 때
  엉뚱한 곳을 건드리지 않는다.
"""

import re
from typing import Any, Dict, List, Optional, Pattern, Tuple

# (카테고리, 정규식)
_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    # --- 크리덴셜 -----------------------------------------------------------
    ("token", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),  # OpenAI
    ("token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),  # GitHub
    ("token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),  # Slack
    ("token", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+")),
    ("token", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),  # AWS Access Key
    ("token", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),  # Google API Key
    ("token", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]{20,}=*")),
    # key = value 형태. 값이 6자 이상일 때만 잡는다.
    # 민감 키워드가 식별자 중간에 있어도 잡아야 한다 (AWS_SECRET_KEY, DB_PASSWORD 등).
    (
        "secret",
        re.compile(
            r"[A-Za-z0-9_.-]*"
            r"(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|private[_-]?key"
            r"|token|credential)"
            r"[A-Za-z0-9_.-]*"
            r"\s*[:=]\s*[\"']?([^\s\"',;]{6,})",
            re.IGNORECASE,
        ),
    ),
    # --- 개인정보 -----------------------------------------------------------
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    # 한국 휴대폰 / 유선 (구분자가 있거나 01X 로 시작하는 경우만)
    ("phone", re.compile(r"\b01[0-9][-.\s]?\d{3,4}[-.\s]?\d{4}\b")),
    ("phone", re.compile(r"\b0\d{1,2}[-.\s]\d{3,4}[-.\s]\d{4}\b")),
    # 국제번호는 + 와 구분자를 요구한다 (숫자 나열 전부를 잡지 않기 위해)
    ("phone", re.compile(r"\+\d{1,3}[-.\s]\d{1,4}[-.\s]\d{3,4}[-.\s]\d{3,4}\b")),
    # --- 내부 리소스 ---------------------------------------------------------
    (
        "internal_url",
        re.compile(
            r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|"
            r"192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})"
            r"(?::\d+)?\S*"
        ),
    ),
    (
        "internal_url",
        re.compile(
            r"https?://[A-Za-z0-9.-]+\.(?:internal|local|corp|intranet|lan)(?::\d+)?\S*",
            re.IGNORECASE,
        ),
    ),
]

_SEVERITY_BY_CATEGORY = {
    "token": "high",
    "secret": "high",
    "internal_url": "med",
    "email": "low",
    "phone": "low",
}

# 문서용 예시임이 명확한 값은 경고하지 않는다.
# 주의: 예전 구현은 "test" 가 포함되기만 하면 전부 건너뛰어서
# latest@company.com 같은 실제 값도 통과시켰다. 여기서는 도메인/자리표시자를
# 정확히 매칭할 때만 제외한다.
_PLACEHOLDER_DOMAINS = (
    "example.com",
    "example.org",
    "example.net",
    "example.co.kr",
    "test.com",
    "localhost.localdomain",
    "email.com",
    "domain.com",
    "yourdomain.com",
)

_PLACEHOLDER_VALUE_PATTERNS: List[Pattern[str]] = [
    re.compile(r"^<[^>]*>$"),  # <your-api-key>
    re.compile(r"^\{\{.*\}\}$"),  # {{API_KEY}}
    re.compile(r"^\$\{.*\}$"),  # ${API_KEY}
    re.compile(r"^\$[A-Z_][A-Z0-9_]*$"),  # $API_KEY
    re.compile(r"^[*x]{3,}$", re.IGNORECASE),  # ***, xxxx
    re.compile(r"^(?:your|my|the)[-_]?", re.IGNORECASE),  # your-secret-key
    re.compile(r"^(?:changeme|placeholder|redacted|dummy|sample|foo|bar|todo)\b", re.IGNORECASE),
]


class SafetyScanner:
    """민감정보 탐지 서비스"""

    def _is_placeholder(self, snippet: str, category: str) -> bool:
        lowered = snippet.lower()

        if category == "email":
            domain = lowered.rsplit("@", 1)[-1]
            return any(domain == d or domain.endswith("." + d) for d in _PLACEHOLDER_DOMAINS)

        if category == "secret":
            # key = value 에서 value 부분만 검사
            _, _, value = snippet.partition("=") if "=" in snippet else snippet.partition(":")
            value = value.strip().strip("\"'")
            if not value:
                return False
            return any(p.search(value) for p in _PLACEHOLDER_VALUE_PATTERNS)

        return any(p.search(snippet.strip().strip("\"'")) for p in _PLACEHOLDER_VALUE_PATTERNS)

    def scan(self, content: str) -> List[Dict[str, Any]]:
        """콘텐츠에서 민감정보를 스캔한다.

        반환: line/column 오름차순으로 정렬된 finding 목록.
        같은 위치에 여러 패턴이 걸리면 심각도가 높은 것 하나만 남긴다.
        """
        if not content:
            return []

        raw: List[Dict[str, Any]] = []
        for line_no, line in enumerate(content.split("\n"), start=1):
            for category, pattern in _PATTERNS:
                for match in pattern.finditer(line):
                    snippet = match.group(0)
                    if self._is_placeholder(snippet, category):
                        continue
                    raw.append(
                        {
                            "category": category,
                            "severity": self._get_severity(category),
                            "snippet": snippet,
                            "location": {
                                "line": line_no,
                                "column": match.start(),
                                "end_column": match.end(),
                            },
                        }
                    )

        return self._dedupe(raw)

    @staticmethod
    def _dedupe(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """겹치는 구간은 (심각도 높은 것 → 긴 것) 우선으로 하나만 남긴다."""
        rank = {"high": 3, "med": 2, "low": 1}
        ordered = sorted(
            findings,
            key=lambda f: (
                f["location"]["line"],
                -rank[f["severity"]],
                -(f["location"]["end_column"] - f["location"]["column"]),
                f["location"]["column"],
            ),
        )

        kept: List[Dict[str, Any]] = []
        for finding in ordered:
            loc = finding["location"]
            overlaps = any(
                k["location"]["line"] == loc["line"]
                and loc["column"] < k["location"]["end_column"]
                and k["location"]["column"] < loc["end_column"]
                for k in kept
            )
            if not overlaps:
                kept.append(finding)

        return sorted(kept, key=lambda f: (f["location"]["line"], f["location"]["column"]))

    @staticmethod
    def _get_severity(category: str) -> str:
        return _SEVERITY_BY_CATEGORY.get(category, "med")

    def mask_content(self, content: str, finding: Dict[str, Any]) -> str:
        """finding 위치의 값을 * 로 치환한다.

        문자열 replace 가 아니라 기록된 오프셋을 사용하므로, 같은 값이 여러 번
        등장해도 지정된 위치만 마스킹된다. 오프셋이 현재 본문과 맞지 않으면
        (편집 등으로 밀린 경우) 원본을 그대로 돌려준다.
        """
        location = finding.get("location") or {}
        snippet = finding.get("snippet") or ""
        line_no = location.get("line")
        start = location.get("column")
        end = location.get("end_column")

        if not line_no or start is None or end is None:
            return content

        lines = content.split("\n")
        if line_no > len(lines):
            return content

        line = lines[line_no - 1]
        if line[start:end] != snippet:
            # 오프셋이 밀렸다면 같은 줄에서 한 번만 fallback 으로 찾아본다.
            found = line.find(snippet)
            if found == -1:
                return content
            start, end = found, found + len(snippet)

        lines[line_no - 1] = line[:start] + "*" * (end - start) + line[end:]
        return "\n".join(lines)

    def remove_finding(self, content: str, finding: Dict[str, Any]) -> str:
        """finding 에 해당하는 값만 본문에서 제거한다 (줄 전체를 지우지 않는다)."""
        location = finding.get("location") or {}
        snippet = finding.get("snippet") or ""
        line_no = location.get("line")
        start = location.get("column")
        end = location.get("end_column")

        if not line_no or start is None or end is None:
            return content

        lines = content.split("\n")
        if line_no > len(lines):
            return content

        line = lines[line_no - 1]
        if line[start:end] != snippet:
            found = line.find(snippet)
            if found == -1:
                return content
            start, end = found, found + len(snippet)

        lines[line_no - 1] = line[:start] + line[end:]
        return "\n".join(lines)
