"""본문에서 기술 스택과 버전을 뽑는다.

왜 필요한가: 기술 글은 "무엇을 어느 버전에서 했는가" 가 전제인데, 대부분 안 적혀 있다.
읽는 사람은 그 글을 믿어도 되는지 판단할 방법이 없고, 쓴 사람은 자기 글이 낡은 걸 모른다.

자동 추출은 **초안**이다. 최종 확정은 작성자가 한다.
자동으로 확정해 버리면 틀린 메타데이터가 조용히 퍼지고, 그건 없는 것보다 나쁘다.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DetectedStack:
    """추출 결과. confidence 는 작성자에게 무엇을 먼저 확인시킬지 정하는 데 쓴다."""

    name: str                       # 정규화된 이름 (react, python)
    version: Optional[str] = None   # "18.3", "3.12". 못 찾으면 None
    confidence: str = "low"         # high | medium | low
    evidence: str = ""              # 어디서 찾았는지 (작성자에게 보여준다)


# 정규화 사전.
#
# 자유 문자열로 두면 "React", "리액트", "react.js" 가 서로 다른 스택이 된다.
# 그러면 "React 18 글 모음" 같은 질의를 못 한다 — 이 제품의 핵심이 그 질의다.
ALIASES: Dict[str, str] = {
    # 언어
    "js": "javascript", "javascript": "javascript", "node": "nodejs", "nodejs": "nodejs",
    "ts": "typescript", "typescript": "typescript",
    "py": "python", "python": "python", "python3": "python",
    "go": "go", "golang": "go",
    "rs": "rust", "rust": "rust",
    "java": "java", "kotlin": "kotlin", "kt": "kotlin",
    "swift": "swift", "rb": "ruby", "ruby": "ruby",
    "php": "php", "cs": "csharp", "csharp": "csharp", "c#": "csharp",
    # 프론트엔드
    "react": "react", "리액트": "react", "react.js": "react", "reactjs": "react",
    "next": "nextjs", "nextjs": "nextjs", "next.js": "nextjs",
    "vue": "vue", "vuejs": "vue", "vue.js": "vue",
    "svelte": "svelte", "sveltekit": "sveltekit",
    "angular": "angular", "solid": "solidjs", "astro": "astro",
    "tailwind": "tailwindcss", "tailwindcss": "tailwindcss",
    # 백엔드
    "fastapi": "fastapi", "django": "django", "flask": "flask",
    "spring": "spring", "springboot": "spring-boot", "spring-boot": "spring-boot",
    "express": "express", "nest": "nestjs", "nestjs": "nestjs",
    "rails": "rails", "laravel": "laravel",
    # 데이터
    "postgres": "postgresql", "postgresql": "postgresql", "psql": "postgresql",
    "mysql": "mysql", "mariadb": "mariadb",
    "redis": "redis", "mongo": "mongodb", "mongodb": "mongodb",
    "elasticsearch": "elasticsearch", "kafka": "kafka",
    "sqlalchemy": "sqlalchemy", "prisma": "prisma", "typeorm": "typeorm",
    # 인프라
    "docker": "docker", "k8s": "kubernetes", "kubernetes": "kubernetes",
    "terraform": "terraform", "nginx": "nginx",
    "aws": "aws", "gcp": "gcp", "azure": "azure",
    # 도구
    "vite": "vite", "webpack": "webpack", "esbuild": "esbuild",
    "jest": "jest", "vitest": "vitest", "pytest": "pytest", "playwright": "playwright",
    "celery": "celery", "graphql": "graphql",
}

# 코드 펜스 언어 → 스택. 언어는 확실한 신호다.
FENCE_LANGUAGES: Dict[str, str] = {
    "javascript": "javascript", "js": "javascript", "jsx": "react",
    "typescript": "typescript", "ts": "typescript", "tsx": "react",
    "python": "python", "py": "python",
    "go": "go", "rust": "rust", "rs": "rust",
    "java": "java", "kotlin": "kotlin", "swift": "swift",
    "ruby": "ruby", "rb": "ruby", "php": "php",
    "sql": "sql", "bash": "shell", "sh": "shell", "shell": "shell",
    "dockerfile": "docker", "yaml": "", "yml": "", "json": "", "html": "", "css": "",
}

_FENCE = re.compile(r"^\s*```([\w+#.-]*)", re.MULTILINE)

# "React 18", "Python 3.12", "Next.js 14.2" — 사람이 본문에 적는 방식
_NAMED_VERSION = re.compile(
    r"\b([A-Za-z][\w.#+-]{1,20}|리액트)\s*[ v]?(\d+(?:\.\d+){0,2})\b"
)

# package.json 의존성 줄:  "react": "^18.3.1"
_NPM_DEP = re.compile(r'"([@\w/.-]+)"\s*:\s*"[\^~>=<]*(\d+(?:\.\d+){0,2})')

# requirements.txt 줄:  fastapi==0.115.6
_PY_DEP = re.compile(r"^([A-Za-z][\w.-]*)\s*[=~>]=\s*(\d+(?:\.\d+){0,2})", re.MULTILINE)

# import 문 — 버전은 모르지만 "쓰였다" 는 확실하다
_JS_IMPORT = re.compile(r"""(?:from|require\()\s*['"]([@\w/.-]+)['"]""")
_PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][\w]*)", re.MULTILINE)

# 컨테이너 이미지 태그:  image: postgres:17-alpine  /  FROM python:3.12-slim
# 인프라 글에서 버전을 알 수 있는 거의 유일한 자리다.
_IMAGE_TAG = re.compile(
    r"(?:^\s*image:\s*|FROM\s+)[\w./-]*?([a-zA-Z][\w-]*):(\d+(?:\.\d+){0,2})",
    re.MULTILINE,
)

# go.mod 의 `go 1.23` 한 줄. go 글이면 거의 항상 있다.
_GO_MOD = re.compile(r"^\s*go\s+(\d+\.\d+(?:\.\d+)?)\s*$", re.MULTILINE)

# lock 파일·YAML 의 `vite: 6.0.3` 형태.
# 아는 이름일 때만 받는다. 아무 key:value 나 받으면 설정값이 버전으로 둔갑한다.
_YAML_VERSION = re.compile(
    r"^\s*[\"']?([a-zA-Z][\w.@/-]*)[\"']?:\s*[\"']?[\^~>=<v]*(\d+(?:\.\d+){0,2})[\"']?\s*$",
    re.MULTILINE,
)

# 쿠버네티스 매니페스트. 버전은 못 주지만 "쿠버네티스 글" 이라는 건 확실하다.
_K8S = re.compile(r"^\s*apiVersion:\s*\S+", re.MULTILINE)

MAX_STACKS = 12


def normalize(raw: str) -> Optional[str]:
    """표기가 어떻든 하나의 이름으로. 모르는 것은 None (추측하지 않는다)."""
    key = raw.strip().lower().lstrip("@")
    # npm 스코프 패키지: @types/react → react 로 뭉개지 않는다. 스코프는 버린다.
    if "/" in key:
        key = key.split("/")[-1]
    return ALIASES.get(key)


def _short_version(version: str) -> str:
    """18.3.1 → 18.3.

    패치 버전까지 기록하면 "낡았다" 판정이 지나치게 민감해진다.
    18.3.1 과 18.3.2 는 글의 유효성 관점에서 같다.
    """
    parts = version.split(".")
    return ".".join(parts[:2]) if len(parts) > 1 else parts[0]


def _add(found: Dict[str, DetectedStack], candidate: DetectedStack) -> None:
    """같은 스택이 여러 곳에서 나오면 더 확실한 쪽을 남긴다."""
    rank = {"high": 3, "medium": 2, "low": 1}
    existing = found.get(candidate.name)
    if existing is None:
        found[candidate.name] = candidate
        return
    # 버전을 찾은 쪽을 우선한다. 버전 없는 high 보다 버전 있는 medium 이 쓸모 있다.
    if (candidate.version and not existing.version) or (
        bool(candidate.version) == bool(existing.version)
        and rank[candidate.confidence] > rank[existing.confidence]
    ):
        found[candidate.name] = candidate


def _code_blocks(markdown: str) -> List[Tuple[str, str]]:
    """(언어, 내용) 목록. 펜스 밖의 산문은 따로 다룬다."""
    blocks: List[Tuple[str, str]] = []
    language = None
    buffer: List[str] = []

    for line in (markdown or "").split("\n"):
        fence = _FENCE.match(line)
        if fence:
            if language is None:
                language = fence.group(1).lower()
                buffer = []
            else:
                blocks.append((language, "\n".join(buffer)))
                language = None
        elif language is not None:
            buffer.append(line)

    if language is not None:  # 닫히지 않은 펜스
        blocks.append((language, "\n".join(buffer)))
    return blocks


def _prose(markdown: str) -> str:
    """코드 블록을 걷어낸 본문.

    코드 안의 숫자를 버전으로 오인하지 않기 위해서다.
    `timeout = 30` 을 "timeout 30" 버전으로 읽으면 안 된다.
    """
    return re.sub(r"```.*?```", " ", markdown or "", flags=re.S)


def detect(markdown: str) -> List[DetectedStack]:
    """본문에서 스택 후보를 뽑는다. 신뢰도 높은 순."""
    found: Dict[str, DetectedStack] = {}

    for language, content in _code_blocks(markdown):
        # 1) 펜스 언어 — 가장 확실하다
        mapped = FENCE_LANGUAGES.get(language)
        if mapped:
            _add(found, DetectedStack(mapped, None, "high", f"```{language} 코드 블록"))

        # 2) 의존성 선언 — 이름과 버전을 함께 준다
        for raw, version in _NPM_DEP.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "package.json"))
        for raw, version in _PY_DEP.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "requirements"))

        # 3) 컨테이너 이미지 태그 — 인프라 글에서 버전을 알 수 있는 거의 유일한 자리
        for raw, version in _IMAGE_TAG.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "이미지 태그"))

        # 4) go.mod
        for version in _GO_MOD.findall(content):
            _add(found, DetectedStack("go", _short_version(version), "high", "go.mod"))

        # 5) lock 파일·YAML 의 `이름: 버전`
        for raw, version in _YAML_VERSION.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, _short_version(version), "medium", "잠금 파일"))

        # 6) 쿠버네티스 매니페스트
        if _K8S.search(content):
            _add(found, DetectedStack("kubernetes", None, "medium", "쿠버네티스 매니페스트"))

        # 7) import — 버전은 없지만 쓰인 건 확실하다
        for raw in _JS_IMPORT.findall(content) + _PY_IMPORT.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, None, "medium", "import 문"))

    # 8) 산문의 "React 18" 같은 표현
    prose = _prose(markdown)
    for raw, version in _NAMED_VERSION.findall(prose):
        name = normalize(raw)
        if name:
            _add(found, DetectedStack(name, _short_version(version), "medium", f"본문의 “{raw} {version}”"))

    # 9) 버전 없이 이름만 언급된 것
    for raw in re.findall(r"\b([A-Za-z][\w.#+-]{1,20})\b", prose):
        name = normalize(raw)
        if name and name not in found:
            _add(found, DetectedStack(name, None, "low", "본문 언급"))

    order = {"high": 0, "medium": 1, "low": 2}
    ranked = sorted(
        found.values(),
        key=lambda s: (order[s.confidence], s.version is None, s.name),
    )
    return ranked[:MAX_STACKS]
