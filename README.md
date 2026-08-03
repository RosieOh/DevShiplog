# Devshiplog

**개발자를 위한 기술 블로그 플랫폼.** 글을 쓰고, 발행하고, 읽고, 반응하는 곳입니다.

AI 가 초안을 만들어 주고, 내 블로그 톤으로 다듬고, 민감정보를 검수한 뒤
`devshiplog.com/@아이디/글주소` 로 바로 발행됩니다.

- **읽는 사람**: 로그인 없이 공개 글을 읽고, 태그·시리즈·검색으로 탐색합니다.
- **쓰는 사람**: 소스(URL·로그)를 넣으면 초안이 생성되고, 편집·검수 후 발행합니다.

## 🚀 기술 스택

- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + TypeScript + NextAuth
- **Backend**: FastAPI (Python 3.11+) + Hexagonal Architecture
- **Database**: MariaDB 10.11+ (SQLAlchemy + Alembic)
- **Queue**: Celery + Redis
- **Storage**: AWS S3 (또는 로컬)

## 📁 프로젝트 구조

```
Devshiplog/
├── frontend/          # Next.js (Feature-based)
├── backend/           # FastAPI (Hexagonal)
├── docs/              # 설계/개발 문서
└── docker-compose.yml # MariaDB + Redis
```

자세한 구조는 [docs/PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md) 참고

## 🛠️ 개발 환경 설정

### 사전 요구사항

- Node.js 18+
- Python 3.11+ (3.12 확인됨)
- Docker & Docker Compose

### 1. 저장소 클론 및 의존성 설치

```bash
# Frontend
cd frontend
npm install

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

각 디렉터리의 `.env.example` 을 복사해서 사용합니다.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

최소한 `backend/.env` 의 `OPENAI_API_KEY` 와 `frontend/.env.local` 의 `NEXTAUTH_SECRET` 은
채워야 동작합니다. `ENVIRONMENT=production` 으로 띄우면 `SECRET_KEY` 가 기본값이거나
32자 미만일 때 **서버가 기동되지 않습니다** (의도된 동작입니다).

### 3. 데이터베이스 실행

```bash
docker-compose up -d
```

### 4. 데이터베이스 마이그레이션

```bash
cd backend
alembic upgrade head
```

### 5. 개발 서버 실행

모든 명령은 `backend/` 디렉터리에서 실행합니다 (`src.` 절대 import 기준).

**Backend**:
```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

**Celery Worker** (별도 터미널):
```bash
cd backend
celery -A src.infrastructure.queue.celery_app worker --loglevel=info
# Windows 에서는 프리포크 풀이 동작하지 않으므로 아래를 사용하세요
# celery -A src.infrastructure.queue.celery_app worker --loglevel=info --pool=solo
```

**Frontend**:
```bash
cd frontend
npm run dev
```

## 📚 주요 기능

### 블로그 플랫폼
- ✅ 공개 블로그 (`/@handle`, `/@handle/글주소`) — 서버 렌더링
- ✅ 발행 / 내리기 / 재발행 (재발행 시 주소 유지)
- ✅ 태그, 시리즈, 검색, 최신·인기 피드
- ✅ 댓글(1단계 답글), 좋아요, 팔로우, 알림
- ✅ 신고 / 차단 / 자동 가림, 레이트리밋
- ✅ SEO: 글별 메타·OG·JSON-LD, sitemap.xml, robots.txt, 블로그별 RSS

### 글쓰기 도구
- ✅ URL/텍스트 입력 → 본문 추출 (SSRF 방어 포함)
- ✅ Style DNA (외부 블로그 RSS 를 읽어 톤 학습 — 온보딩 임포트)
- ✅ Draft 생성 (SSE 실시간 스트리밍)
- ✅ 마크다운 에디터 + Preview + 자동저장
- ✅ 버전 스냅샷 / 되돌리기
- ✅ Safety 검사 (민감정보 탐지/마스킹) — **발행 전 게이트**
- ✅ Export (Copy/Download)
- ✅ 사용량 추적 및 월간 쿼터

### 핵심 설계: Draft 와 Post 는 별개다

```
Draft (비공개 작업본)  ──발행──▶  Post (공개 스냅샷)
  · 2초마다 자동저장                 · slug, 발행일시, 공개 URL
  · AI 생성/변형 대상                · 캐시 대상 (검색 크롤러가 읽는 대상)
```

한 테이블로 합치면 편집 중 자동저장이 **공개된 글을 실시간으로 바꿔버리고**,
캐시 무효화 시점도 잡을 수 없습니다.

## 🔐 보안 관련 메모

- `/api/v1/public/*` 를 제외한 모든 엔드포인트는 인증이 필요하며, 리소스마다 소유권을 검사합니다.
  공개 경로는 비공개 정보(이메일 등)를 절대 반환하지 않습니다.
- 소유권 불일치는 403 이 아니라 **404** 로 답합니다. 403 은 "그 리소스는 존재한다" 를 알려주는 셈입니다.
- 마크다운은 원시 HTML 을 통과시키지 않습니다 (저장형 XSS 차단).
- 댓글·신고·팔로우·발행·로그인에 Redis 기반 레이트리밋이 걸려 있습니다.
- 크롤러는 요청 전 DNS 를 확인해 사설/루프백/링크로컬 대역을 차단합니다
  (`CRAWLER_ALLOW_PRIVATE_NETWORK=false`). 리다이렉트도 매 홉 검사합니다.
- SSE 는 브라우저 `EventSource` 가 헤더를 못 붙이므로 `?token=` 쿼리 인증을 허용합니다.
  이 방식은 SSE 엔드포인트에서만 열려 있습니다.

## 🧪 테스트

```bash
# Backend
cd backend
pytest

# Frontend (타입 검사 / 빌드)
cd frontend
npm run type-check
npm run build
```

## 📖 문서

- [개발 가이드](./docs/DEVELOPMENT_GUIDE.md)
- [프로젝트 구조](./docs/PROJECT_STRUCTURE.md)
- [구현 가능성 검토](./docs/IMPLEMENTATION_FEASIBILITY.md)
- API 문서: 서버 실행 후 http://localhost:8000/docs (프로덕션에서는 비활성화)

## 🎯 개발 로드맵

- **완료**: 글쓰기 도구 + 블로그 플랫폼(발행·공개 읽기·SEO·소셜·모더레이션)
- **다음**: 이미지 업로드(S3), 커버 이미지, 시리즈 편집 UI, 운영자 신고 처리 화면
- **이후**: GitHub OAuth, 크로스포스팅, 전문검색(FULLTEXT) 전환

## 📝 라이선스

MIT
