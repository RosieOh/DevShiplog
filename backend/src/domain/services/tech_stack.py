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
    "gunicorn": "gunicorn", "uvicorn": "uvicorn", "uwsgi": "uwsgi",
    # JVM·Rust·Ruby·.NET 생태계
    "spring-boot-starter-parent": "spring-boot", "spring-boot-starter-web": "spring-boot",
    "spring-boot-starter": "spring-boot",
    "spring-boot": "spring-boot", "springboot": "spring-boot",
    "spring boot": "spring-boot", "spring framework": "spring", "spring": "spring",
    # Gradle 플러그인 id 는 역DNS 다. 마지막 조각("boot")을 별칭으로 걸면
    # "Spring Framework" 의 Framework 처럼 일반 명사가 오탐을 만든다.
    # 전체 id 를 그대로 적는 편이 안전하다.
    "org.springframework.boot": "spring-boot",
    "io.spring.dependency-management": "spring",
    "react native": "react-native", "react-native": "react-native",
    "tokio": "tokio", "serde": "serde", "axum": "axum",
    "dotnet": "dotnet", "aspnetcore": "dotnet",
    "puma": "puma", "sidekiq": "sidekiq",
    "laravel": "laravel", "symfony": "symfony",
    "java": "java",
    # 한글 표기. 실제 글에 "자바 17 버전", "스프링에서" 처럼 쓴다.
    # 한국어 블로그가 대상인 제품이 이걸 못 읽으면 산문에서 절반을 놓친다.
    "자바": "java", "코틀린": "kotlin", "파이썬": "python", "파이선": "python",
    "스프링": "spring", "스프링부트": "spring-boot", "장고": "django",
    "리액트": "react", "리엑트": "react", "뷰": "vue", "스벨트": "svelte",
    "노드": "nodejs", "타입스크립트": "typescript", "자바스크립트": "javascript",
    "도커": "docker", "쿠버네티스": "kubernetes", "쿠베": "kubernetes",
    "레디스": "redis", "몽고": "mongodb", "포스트그레스": "postgresql",
    "고랭": "go", "러스트": "rust", "루비": "ruby",
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
# "React 18", "Python 3.12", "React 18버전", "Next v14"
#
# `\b` 를 쓰지 않는다. 파이썬 정규식은 한글도 단어 문자로 보기 때문에
# "18버전" 의 8과 버 사이, "3.12를" 의 2와 를 사이에 경계가 생기지 않는다.
# 그래서 "React 18버전" 은 버전을 통째로 놓쳤고 "Python 3.12를" 은 3만 잡혔다.
# 한국어 개발 블로그가 대상인 제품에서 이건 치명적이다.
#
# 대신 ASCII 기준으로 명시한다.
#   앞: ASCII 영숫자가 아니어야 한다 (단어 중간을 잡지 않게)
#   뒤: 숫자나 점이 아니어야 한다 (3.12 를 3 으로 자르지 않게)
# 이름과 버전 사이에 조사가 끼는 것도 받는다. "React 도 18", "Next 는 14".
# 한국어로 쓰면 흔한 형태인데, 이걸 놓치면 산문에서 버전을 거의 못 뽑는다.
_PARTICLE = r"(?:\s*(?:은|는|이|가|을|를|도|의|에서|로|으로)\s*)?"
# 두 단어 이름을 받는다. "Spring Boot 3.2.x", "Spring Framework 6.1", "React Native 0.76".
# 한 토큰만 보면 "Boot" 나 "Framework" 를 잡게 되는데, 그건 일반 명사라
# 별칭으로 걸 수 없다 (실제로 "Spring Framework 6.1" 을 laravel 로 잡은 적이 있다).
_NAMED_VERSION = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9.#+_-]{1,20}(?:\s+[A-Z][A-Za-z]{1,12})?|[가-힣]{2,8})"
    + _PARTICLE
    # `3.2.x` 를 받는다. "Spring Boot 3.2.x 버전" 은 한국어 글에서 아주 흔하고,
    # 뜻은 "3.2 계열" 이므로 3.2 로 읽으면 된다.
    + r"\s*v?\s*(\d+(?:\.\d+){0,2})(?:\.x)?(?![\d.])"
    # "Java 8 이상" 은 최소 요구사항이지 이 글의 전제가 아니다.
    # 이걸 전제로 잡으면 Spring Boot 3 글이 "Java 8 기준" 이 되어 정반대가 된다.
    + r"(?!\s*(?:이상|이하|미만|초과))"
)

# 마이그레이션 글의 "14 에서 15 로", "18 → 19".
# 이런 글의 전제는 **올린 뒤** 버전이다. 앞 숫자를 잡으면 정반대가 된다.
_UPGRADE = re.compile(r"(\d+(?:\.\d+){0,2})\s*(?:에서|->|→)\s*(\d+(?:\.\d+){0,2})(?![\d.])")

# --- 빌드 파일 -----------------------------------------------------------
# JVM·Rust·Ruby·.NET 생태계는 앞선 규칙으로 하나도 안 잡혔다.
# 사용자 층이 작지 않으므로 각각의 관용 표기를 따로 본다.

# Gradle:  id 'org.springframework.boot' version '3.4.1'
#          implementation 'com.example:artifact:1.2.3'
_GRADLE_PLUGIN = re.compile(r"""id\s*[('"]+([\w.-]+)['")\s]+version\s*['"]([\d.]+)['"]""")
_GRADLE_DEP = re.compile(r"""['"]([\w.-]+):([\w.-]+):([\d][\d.]*)['"]""")
# JavaVersion.VERSION_21 / sourceCompatibility = 17
_JAVA_VERSION = re.compile(r"(?:JavaVersion\.VERSION_|sourceCompatibility\s*=\s*)(\d+)")

# Maven:  <artifactId>spring-boot-starter-parent</artifactId> ... <version>3.2.5</version>
_MAVEN_ARTIFACT = re.compile(
    r"<artifactId>([\w.-]+)</artifactId>\s*<version>([\d.]+)</version>", re.S
)
_MAVEN_PROPERTY = re.compile(r"<([\w.]+)\.version>([\d.]+)</[\w.]+\.version>")

# Cargo:  tokio = { version = "1.42" }  /  serde = "1.0"  /  rust-version = "1.83"
_CARGO_DEP = re.compile(
    r"""^\s*([\w-]+)\s*=\s*(?:\{[^}]*version\s*=\s*)?["']([\d.]+)["']""", re.MULTILINE
)

# Gemfile:  ruby '3.3.6'  /  gem 'rails', '~> 7.2.2'
_GEMFILE_RUBY = re.compile(r"""^\s*ruby\s+['"]([\d.]+)['"]""", re.MULTILINE)
_GEMFILE_GEM = re.compile(r"""^\s*gem\s+['"]([\w-]+)['"](?:\s*,\s*['"][~><=^\s]*([\d.]+)['"])?""",
                          re.MULTILINE)

# .NET:  <TargetFramework>net8.0</TargetFramework>
#        <PackageReference Include="X" Version="8.0.3" />
_DOTNET_TFM = re.compile(r"<TargetFramework>net([\d.]+)</TargetFramework>")
_DOTNET_PKG = re.compile(r"""<PackageReference\s+Include=["']([\w.]+)["']\s+Version=["']([\d.]+)["']""")

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

# 태그 없는 이미지:  image: redis
# 버전은 모르지만 쓰인 것은 확실하다. 놓치면 인프라 글에서 스택이 텅 빈다.
_IMAGE_PLAIN = re.compile(r"^\s*image:\s*([a-zA-Z][\w-]*)\s*$", re.MULTILINE)

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
    key = " ".join(raw.strip().lower().split())
    key = key.lstrip("@")
    if "/" in key:
        vendor, _, package = key.partition("/")
        # @types/react 는 뒤(react)가, laravel/framework 는 앞(laravel)이 답이다.
        # 둘 다 시도하되 뒤를 먼저 본다 — npm 쪽이 훨씬 흔하다.
        return ALIASES.get(package) or ALIASES.get(vendor)
    if key in ALIASES:
        return ALIASES[key]
    # "Spring Boot" 는 알지만 "Spring Cloud" 는 모른다.
    # 두 단어를 모르면 첫 단어로 되돌아간다 — "Spring Cloud 4" 는 spring 으로 읽는 편이
    # 아무것도 안 읽는 것보다 낫다.
    if " " in key:
        return ALIASES.get(key.split()[0])
    return None


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

        for raw in _IMAGE_PLAIN.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, None, "high", "이미지 (태그 없음)"))

        # 4) go.mod
        for version in _GO_MOD.findall(content):
            _add(found, DetectedStack("go", _short_version(version), "high", "go.mod"))

        # 5) lock 파일·YAML 의 `이름: 버전`
        for raw, version in _YAML_VERSION.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, _short_version(version), "medium", "잠금 파일"))

        # 6) 빌드 파일 — 생태계마다 관용 표기가 전혀 다르다
        for raw, version in _GRADLE_PLUGIN.findall(content):
            # 플러그인 id 는 org.springframework.boot 처럼 전체 경로다.
            # 마지막 조각(boot)에 별칭을 걸어 두었으므로 그쪽도 시도한다.
            name = normalize(raw) or normalize(raw.split(".")[-1])
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "Gradle"))
        for group, artifact, version in _GRADLE_DEP.findall(content):
            # group 이 org.springframework.boot 이고 artifact 가 starter-web 인 식이라
            # 둘 다 시도한다.
            name = normalize(artifact) or normalize(group.split(".")[-1])
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "Gradle"))
        for version in _JAVA_VERSION.findall(content):
            _add(found, DetectedStack("java", version, "high", "Gradle"))

        for artifact, version in _MAVEN_ARTIFACT.findall(content):
            name = normalize(artifact) or normalize(artifact.split("-")[0])
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "Maven"))
        for prop, version in _MAVEN_PROPERTY.findall(content):
            name = normalize(prop)
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "Maven"))

        for raw, version in _CARGO_DEP.findall(content):
            name = "rust" if raw == "rust-version" else normalize(raw)
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", "Cargo.toml"))

        for version in _GEMFILE_RUBY.findall(content):
            _add(found, DetectedStack("ruby", _short_version(version), "high", "Gemfile"))
        for raw, version in _GEMFILE_GEM.findall(content):
            name = normalize(raw)
            if name:
                _add(
                    found,
                    DetectedStack(name, _short_version(version) if version else None,
                                  "high", "Gemfile"),
                )

        for version in _DOTNET_TFM.findall(content):
            _add(found, DetectedStack("dotnet", _short_version(version), "high", ".NET csproj"))
            _add(found, DetectedStack("csharp", None, "medium", ".NET csproj"))
        for raw, version in _DOTNET_PKG.findall(content):
            name = normalize(raw) or normalize(raw.split(".")[0])
            if name:
                _add(found, DetectedStack(name, _short_version(version), "high", ".NET csproj"))

        # 7) 쿠버네티스 매니페스트
        if _K8S.search(content):
            _add(found, DetectedStack("kubernetes", None, "medium", "쿠버네티스 매니페스트"))

        # 8) import — 버전은 없지만 쓰인 건 확실하다
        for raw in _JS_IMPORT.findall(content) + _PY_IMPORT.findall(content):
            name = normalize(raw)
            if name:
                _add(found, DetectedStack(name, None, "medium", "import 문"))

    # 9) 산문의 "React 18" 같은 표현
    prose = _prose(markdown)
    for raw, version in _NAMED_VERSION.findall(prose):
        name = normalize(raw)
        if name:
            _add(found, DetectedStack(name, _short_version(version), "medium", f"본문의 “{raw} {version}”"))

    # 10) 버전 없이 이름만 언급된 것
    # 여기도 \b 를 쓰면 "Django의" 가 통째로 잡혀 정규화에 실패한다.
    for raw in re.findall(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9.#+_-]{1,20})", prose):
        name = normalize(raw)
        if name and name not in found:
            _add(found, DetectedStack(name, None, "low", "본문 언급"))

    # 마이그레이션 글: "14 에서 15 로" 는 15 가 전제다.
    # 산문에서 위 규칙은 앞 숫자(14)를 잡으므로 여기서 바로잡는다.
    for before, after in _UPGRADE.findall(prose):
        for stack in list(found.values()):
            if stack.version and _short_version(before).startswith(stack.version.split(".")[0]):
                found[stack.name] = DetectedStack(
                    stack.name, _short_version(after), stack.confidence,
                    f"{stack.evidence} (마이그레이션 후 버전)",
                )

    order = {"high": 0, "medium": 1, "low": 2}
    ranked = sorted(
        found.values(),
        key=lambda s: (order[s.confidence], s.version is None, s.name),
    )
    return ranked[:MAX_STACKS]
