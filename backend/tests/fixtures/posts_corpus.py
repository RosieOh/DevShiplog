"""추출기 평가용 코퍼스.

실제 한국어 개발 블로그 글이 어떻게 생겼는지를 흉내 낸 표본이다.
합성이지만 E2E 찌꺼기("1편", "충돌")보다는 훨씬 정직하다.

각 항목의 `expect` 는 **사람이 읽고 판단한 정답**이다.
추출기가 이걸 얼마나 맞히는지가 곧 제품이 동작하는 비율이다.

새 글 형태를 만나면 여기 추가한다. 이 파일이 커질수록 추출기 판단이 정확해진다.
"""

from typing import Dict, List, Optional, TypedDict


class Sample(TypedDict):
    name: str
    body: str
    # 사람이 읽고 판단한 정답. None 이면 "버전을 알 수 없다" 가 맞는 답이다.
    expect: Dict[str, Optional[str]]


CORPUS: List[Sample] = [
    {
        "name": "트러블슈팅 · package.json 포함",
        "expect": {"react": "18.3", "nextjs": "14.2"},
        "body": """## 문제

프로덕션에서만 하이드레이션 오류가 났습니다.

```
Error: Text content does not match server-rendered HTML
```

## 환경

```json
{
  "dependencies": {
    "next": "14.2.3",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }
}
```

## 원인

`new Date()` 를 서버와 클라이언트가 각각 부르고 있었습니다.
""",
    },
    {
        "name": "튜토리얼 · 산문에만 버전",
        "expect": {"fastapi": None, "python": "3.12"},
        "body": """FastAPI 로 파일 업로드를 받는 방법을 정리합니다. Python 3.12 기준입니다.

```python
from fastapi import FastAPI, UploadFile

app = FastAPI()

@app.post("/upload")
async def upload(file: UploadFile):
    return {"size": file.size}
```

여기서 주의할 점은 `UploadFile` 이 스트림이라는 것입니다.
""",
    },
    {
        "name": "설정 가이드 · lock 파일",
        "expect": {"vite": "6.0", "vue": "3.5"},
        "body": """빌드가 느려서 설정을 손봤습니다.

```
# pnpm-lock.yaml
vite: 6.0.3
vue: 3.5.13
```

`optimizeDeps` 를 켜니 콜드 스타트가 절반으로 줄었습니다.
""",
    },
    {
        "name": "인프라 · Dockerfile + compose",
        "expect": {"docker": None, "postgresql": "17", "redis": "7", "python": "3.12"},
        "body": """로컬 개발 환경을 컨테이너로 옮겼습니다.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
```

```yaml
services:
  db:
    image: postgres:17
  cache:
    image: redis:7-alpine
```
""",
    },
    {
        "name": "비교글 · 이름만, 버전 없음",
        "expect": {"vite": None, "webpack": None},
        "body": """Vite 와 Webpack 을 둘 다 써보고 느낀 점을 적습니다.

Webpack 은 설정이 길지만 통제가 됩니다. Vite 는 시작이 빠릅니다.
결국 팀 규모와 빌드 복잡도에 따라 갈립니다.

코드는 없습니다. 경험만 적습니다.
""",
    },
    {
        "name": "알고리즘 풀이 · 프레임워크 없음",
        "expect": {"python": None},
        "body": """이분 탐색으로 푸는 문제입니다.

```python
def search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

시간 복잡도는 O(log n) 입니다.
""",
    },
    {
        "name": "회고 · 코드 거의 없음",
        "expect": {},
        "body": """올해 팀을 옮기면서 배운 것을 적습니다.

가장 크게 느낀 것은 코드보다 맥락이 중요하다는 점이었습니다.
새 코드베이스에 들어갔을 때 제일 먼저 한 일은 회의록을 읽는 것이었습니다.

기술적인 내용은 거의 없습니다.
""",
    },
    {
        "name": "백엔드 · requirements + import",
        "expect": {"django": "5.1", "celery": None, "postgresql": None, "python": None},
        "body": """비동기 작업을 Celery 로 옮긴 기록입니다.

```
django==5.1.4
celery==5.4.0
psycopg[binary]==3.2.3
```

```python
from celery import shared_task
from django.db import transaction

@shared_task
def send_report(user_id):
    with transaction.atomic():
        ...
```

PostgreSQL 커넥션 풀이 금방 마르는 문제가 있었습니다.
""",
    },
    {
        "name": "프론트 · TS + Tailwind, 버전은 산문",
        "expect": {"typescript": "5.4", "tailwindcss": "4", "react": None},
        "body": """디자인 시스템을 Tailwind 4 로 올렸습니다. TypeScript 5.4 를 씁니다.

```tsx
export function Button({ children }: { children: React.ReactNode }) {
  return <button className="rounded px-4 py-2">{children}</button>
}
```

`@theme` 블록으로 토큰을 옮기는 게 제일 오래 걸렸습니다.
""",
    },
    {
        "name": "Go · go.mod",
        "expect": {"go": "1.23"},
        "body": """고루틴 누수를 잡은 기록입니다.

```
module example.com/app

go 1.23
```

```go
func worker(ctx context.Context, ch <-chan Job) {
    for {
        select {
        case <-ctx.Done():
            return
        case job := <-ch:
            handle(job)
        }
    }
}
```

`ctx.Done()` 을 안 받으면 고루틴이 안 죽습니다.
""",
    },
    {
        "name": "쿠버네티스 · 매니페스트",
        "expect": {"kubernetes": None, "nginx": None},
        "body": """무중단 배포 설정입니다.

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  strategy:
    rollingUpdate:
      maxUnavailable: 0
```

앞단은 nginx 인그레스를 씁니다.
""",
    },
    {
        "name": "노이즈 · 숫자가 많지만 버전이 아님",
        "expect": {"python": None},
        "body": """성능 측정 결과를 정리합니다.

```python
timeout = 30
batch_size = 500
retries = 3
```

평균 응답이 120ms 에서 45ms 로 줄었습니다. p99 는 890ms 입니다.
""",
    },
]

# ─────────────────────────────────────────────────────────────────────────
# 아래는 **처음 코퍼스를 만들 때 생각하지 못한** 형태들이다.
#
# 첫 12건은 내가 예상한 모양만 담고 있었고, 거기서 100% 가 나온 것은
# "예상한 것은 잡는다" 는 뜻일 뿐이었다. 예상 밖을 넣어야 진짜 수치가 나온다.
# ─────────────────────────────────────────────────────────────────────────

CORPUS += [
    # --- 다른 생태계 ------------------------------------------------------
    {
        "name": "Java · Gradle",
        "expect": {"java": "21", "spring-boot": "3.4", "kotlin": None},
        "body": """멀티모듈로 쪼갠 기록입니다.

```groovy
plugins {
    id 'org.springframework.boot' version '3.4.1'
}

java {
    sourceCompatibility = JavaVersion.VERSION_21
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
}
```

Kotlin DSL 로 옮길지 고민 중입니다.
""",
    },
    {
        "name": "Java · Maven pom.xml",
        "expect": {"java": "17", "spring-boot": "3.2"},
        "body": """의존성 정리 기록입니다.

```xml
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>3.2.5</version>
</parent>
<properties>
  <java.version>17</java.version>
</properties>
```
""",
    },
    {
        "name": "Rust · Cargo.toml",
        "expect": {"rust": "1.83", "tokio": "1.42"},
        "body": """비동기 런타임을 붙였습니다.

```toml
[package]
edition = "2021"
rust-version = "1.83"

[dependencies]
tokio = { version = "1.42", features = ["full"] }
```
""",
    },
    {
        "name": "Ruby · Gemfile",
        "expect": {"ruby": "3.3", "rails": "7.2", "puma": None},
        "body": """레일즈 업그레이드 기록입니다.

```ruby
ruby '3.3.6'
gem 'rails', '~> 7.2.2'
gem 'puma'
```
""",
    },
    {
        "name": ".NET · csproj",
        "expect": {"csharp": None, "dotnet": "8.0"},
        "body": """최소 API 로 다시 썼습니다.

```xml
<PropertyGroup>
  <TargetFramework>net8.0</TargetFramework>
</PropertyGroup>
<ItemGroup>
  <PackageReference Include="Serilog.AspNetCore" Version="8.0.3" />
</ItemGroup>
```
""",
    },
    {
        "name": "PHP · composer.json",
        "expect": {"php": "8.3", "laravel": "11.0"},
        "body": """라라벨 버전을 올렸습니다.

```json
{
  "require": {
    "php": "^8.3",
    "laravel/framework": "^11.0"
  }
}
```
""",
    },

    # --- 한국어 버전 표기 --------------------------------------------------
    {
        "name": "한국어 표기 · “18버전”, “v14”",
        "expect": {"react": "18", "nextjs": "14"},
        "body": """React 18버전에서 Next v14 로 올린 기록입니다.

동시성 기능이 들어오면서 렌더링 타이밍이 바뀌었습니다.
""",
    },
    {
        "name": "한국어 표기 · 마이그레이션 (before → after)",
        "expect": {"nextjs": "15", "react": "19"},
        "body": """Next 14 에서 15 로 올렸습니다. React 도 18 에서 19 가 됐습니다.

가장 크게 바뀐 것은 캐싱 기본값입니다.

> 글의 전제는 **올린 뒤** 버전입니다. 이전 버전이 아닙니다.
""",
    },
    {
        "name": "한국어 표기 · 조사가 붙음",
        "expect": {"python": "3.12", "django": None},
        "body": """Python 3.12를 쓰면서 Django의 비동기 뷰를 정리합니다.

타입 힌트가 편해졌습니다.
""",
    },

    # --- 함정: 버전처럼 보이지만 아닌 숫자 ----------------------------------
    {
        "name": "함정 · 날짜·시간·비율",
        "expect": {"python": None},
        "body": """2024.01.15 에 시작해서 3.5초 걸리던 작업을 0.8초로 줄였습니다.
가용성은 99.9% 를 유지했습니다.

```python
import statistics
```

RFC 7231 을 참고했습니다.
""",
    },
    {
        "name": "함정 · 포트 번호와 IP",
        "expect": {"nginx": None, "docker": None},
        "body": """nginx 를 앞에 두고 localhost:3000 으로 프록시했습니다.
내부망은 10.0.1.24 입니다.

```dockerfile
EXPOSE 8080
```
""",
    },
    {
        "name": "함정 · 표 안의 숫자",
        "expect": {"redis": None},
        "body": """벤치마크 결과입니다.

| 동시성 | p50 | p99 |
|---|---|---|
| 100 | 12 | 45 |
| 500 | 31 | 180 |

redis 캐시를 앞에 두니 확실히 나아졌습니다.
""",
    },

    # --- 혼합 -------------------------------------------------------------
    {
        "name": "풀스택 · 여러 서비스",
        "expect": {
            "nextjs": "15.1", "react": "19.0", "fastapi": "0.115",
            "postgresql": "17", "redis": "7.4", "docker": None, "python": None,
        },
        "body": """모노레포 구성을 정리합니다.

```json
{ "dependencies": { "next": "15.1.0", "react": "19.0.0" } }
```

```
fastapi==0.115.6
```

```yaml
services:
  db:
    image: postgres:17-alpine
  cache:
    image: redis:7.4
```

```dockerfile
FROM python:3.12-slim
```
""",
    },
    {
        "name": "짧은 글 · 스니펫만",
        "expect": {"typescript": None},
        "body": """자주 까먹어서 적어둡니다.

```ts
const unique = <T,>(xs: T[]) => [...new Set(xs)]
```
""",
    },
]
