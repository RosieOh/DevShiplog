# Devshiplog

**낡지 않는 기술 블로그 플랫폼.**

기술 글은 시간이 지나면 틀린 글이 됩니다. 그런데 아무도 그걸 관리하지 않습니다.
검색해서 나온 글을 따라 했는데 안 되고, 스크롤을 올려 날짜를 보면 2023년이고,
어느 버전 기준인지는 안 적혀 있습니다.

Devshiplog 는 글을 텍스트 덩어리가 아니라
**"어떤 스택의 어떤 버전에서, 언제 확인된 절차"** 로 다룹니다.

| | 보통의 블로그 | Devshiplog |
|---|---|---|
| 글의 전제 | 안 적혀 있음 | `react@18.3 · node@20` 으로 구조화 |
| 신뢰도 | 작성 날짜 한 줄 | 마지막 **검증** 시각 + 스택 최신성 |
| 낡은 글 | 방치 | 독자에게 경고, 작성자에게 갱신 목록 |
| "안 돼요" | 댓글에 묻힘 | 구조화된 신호 → 작성자 대시보드 |
| 탐색 | 태그 (자유 문자열) | 스택 + 버전 (정규화) |

전략과 수익 모델은 [docs/PRODUCT_STRATEGY.md](./docs/PRODUCT_STRATEGY.md) 참고.

### 쓰는 흐름

1. **쓴다** — URL·로그·PR 을 넣으면 초안이 나옵니다. 전에 쓴 글에서 문체를 배웁니다.
2. **전제를 남긴다** — 본문에서 기술과 버전을 자동으로 찾습니다. 확인만 하면 됩니다.
3. **확인한다** — 다시 돌려보고 "지금도 된다"를 누릅니다. 글을 고치지 않아도 됩니다.
4. **알림을 받는다** — 버전이 올라가거나 독자가 "안 됐어요"를 누르면 갱신 목록에 올라옵니다.

공개 주소는 `devshiplog.com/@아이디/글주소` 입니다. 개인 블로그는 무료입니다.

## 🚀 기술 스택

- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + TypeScript + NextAuth
- **Backend**: FastAPI (Python 3.11+) + Hexagonal Architecture
- **Database**: MariaDB 10.11+ (SQLAlchemy + Alembic)
- **Queue**: Celery + Redis
- **Storage**: MinIO (S3 호환) — 개발·운영 동일 코드, AWS S3 로 전환 가능

## 📁 프로젝트 구조

```
Devshiplog/
├── frontend/          # Next.js (Feature-based)
├── backend/           # FastAPI (Hexagonal)
├── docs/              # 설계/개발 문서
├── e2e/               # 통합 검증 (API + 브라우저)
└── docker-compose.yml # MariaDB + Redis + MinIO + Mailpit
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

기본값은 `docker compose` 로 뜨는 MariaDB·Redis·MinIO 를 가리킵니다.
MinIO 버킷은 백엔드가 기동할 때 자동으로 만들어지므로 따로 준비할 것이 없습니다.
콘솔은 http://localhost:9001 (devshiplog / devshiplog1234) 입니다.

> **배포 전 확인**: `STORAGE_PUBLIC_BASE_URL` 이 글 본문에 그대로 박히는 주소입니다.
> localhost 인 채로 발행하면 독자에게 이미지가 깨져 보이고, 나중에 고쳐도 DB 에 남습니다.
> `ENVIRONMENT=production` 이면 기동 시 이 값을 검사해 막습니다.

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
- **다음**: 시리즈 편집 UI, 운영자 신고 처리 화면
- **이후**: GitHub OAuth, 크로스포스팅, 전문검색(FULLTEXT) 전환

## 📝 라이선스

MIT
