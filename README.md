# Devshiplog

URL/PR/로그를 넣으면, 내 블로그 톤으로 기술 글 초안을 생성하고 안전/SEO 검수까지 마친 뒤 발행(또는 복사)까지 이어주는 플랫폼

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

### MVP (P0)
- ✅ URL/텍스트 입력 → 본문 추출 (SSRF 방어 포함)
- ✅ Style DNA 생성 (블로그 RSS 분석)
- ✅ Draft 생성 (SSE 실시간 스트리밍)
- ✅ 마크다운 에디터 + Preview + 자동저장
- ✅ 버전 스냅샷 / 되돌리기
- ✅ Safety 검사 (민감정보 탐지/마스킹)
- ✅ Export (Copy/Download)
- ✅ 사용량 추적 및 월간 쿼터

## 🔐 보안 관련 메모

- 모든 `/api/v1/*` 엔드포인트는 인증이 필요하며, 리소스마다 소유권을 검사합니다.
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

- **MVP**: P0 기능 — 완료
- **V1**: GitHub OAuth, SEO 탭, 템플릿 확장
- **V2**: 자동 수집, API 발행, 크롬 확장

## 📝 라이선스

MIT
