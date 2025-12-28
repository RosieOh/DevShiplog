from typing import List, Dict, Any
import re


class SafetyScanner:
    """민감정보 탐지 서비스"""

    # 패턴 정의
    PATTERNS = {
        "token": [
            r"sk-[a-zA-Z0-9]{32,}",  # OpenAI API Key
            r"ghp_[a-zA-Z0-9]{36,}",  # GitHub Personal Access Token
            r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}",  # Slack Token
            r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",  # Bearer Token
        ],
        "email": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ],
        "phone": [
            r"(\+82|0)?[0-9]{2,3}-?[0-9]{3,4}-?[0-9]{4}",  # 한국 전화번호
            r"\+?[1-9]\d{1,14}",  # 국제 전화번호
        ],
        "internal_url": [
            r"https?://(?:localhost|127\.0\.0\.1|192\.168\.|10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)",
            r"https?://(?:internal|dev|staging|test)\.",  # 내부 도메인 패턴
        ],
        "secret": [
            r"password\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
            r"secret\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
            r"api[_-]?key\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
        ],
    }

    def scan(self, content: str) -> List[Dict[str, Any]]:
        """콘텐츠에서 민감정보 스캔"""
        findings = []
        lines = content.split("\n")

        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for line_no, line in enumerate(lines, start=1):
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        snippet = match.group(0)
                        # 일부 허용 패턴 제외 (예: example.com)
                        if "example" in snippet.lower() or "test" in snippet.lower():
                            continue

                        findings.append({
                            "category": category,
                            "severity": self._get_severity(category),
                            "snippet": snippet,
                            "location": {
                                "line": line_no,
                                "column": match.start(),
                                "end_column": match.end(),
                            },
                        })

        return findings

    def _get_severity(self, category: str) -> str:
        """카테고리에 따른 심각도 반환"""
        severity_map = {
            "token": "high",
            "secret": "high",
            "internal_url": "med",
            "email": "low",
            "phone": "low",
        }
        return severity_map.get(category, "med")

    def mask_content(self, content: str, finding: Dict[str, Any]) -> str:
        """민감정보 마스킹"""
        location = finding["location"]
        lines = content.split("\n")
        
        if location["line"] <= len(lines):
            line = lines[location["line"] - 1]
            snippet = finding["snippet"]
            masked = "*" * len(snippet)
            lines[location["line"] - 1] = line.replace(snippet, masked, 1)
        
        return "\n".join(lines)

