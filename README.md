# Devshiplog

URL/PR/로그를 넣으면, 내 블로그 톤으로 기술 글 초안을 생성하고 안전/SEO 검수까지 마친 뒤 발행(또는 복사)까지 이어주는 플랫폼

## 🚀 기술 스택

- **Frontend**: Next.js 14+ (App Router) + Tailwind CSS + TypeScript
- **Backend**: FastAPI (Python 3.11+) + Hexagonal Architecture
- **Database**: MariaDB 10.11+
- **Queue**: Celery + Redis
- **Storage**: AWS S3 (또는 로컬)

## 📁 프로젝트 구조

```
Devshiplog/
├── frontend/          # Next.js (Feature-based)
├── backend/           # FastAPI (Hexagonal)
├── shared/            # 공통 타입/유틸리티
└── docker-compose.yml
```

자세한 구조는 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) 참고

## 🛠️ 개발 환경 설정

### 사전 요구사항

- Node.js 18+
- Python 3.11+
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

**Backend** (`backend/.env`):
```env
DATABASE_URL=mysql+pymysql://devshiplog:devshiplog@localhost:3306/devshiplog
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
SECRET_KEY=your-secret-key
```

**Frontend** (`frontend/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

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

**Backend**:
```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
npm run dev
```

**Celery Worker** (별도 터미널):
```bash
cd backend
celery -A infrastructure.queue.celery_app worker --loglevel=info
```

## 📚 주요 기능

### MVP (P0)
- ✅ URL/텍스트 입력 → 본문 추출
- ✅ Style DNA 생성 (블로그 주소 분석)
- ✅ Draft 생성 (스트리밍)
- ✅ 마크다운 에디터 + Preview
- ✅ Safety 검사 (민감정보 탐지/마스킹)
- ✅ 버전 관리
- ✅ Export (Copy/Download)

## 🧪 테스트

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 📖 문서

- [구현 가능성 검토](./IMPLEMENTATION_FEASIBILITY.md)
- [프로젝트 구조](./PROJECT_STRUCTURE.md)
- [API 문서](./backend/API_DOCS.md) (작성 예정)

## 🎯 개발 로드맵

- **MVP (4-6주)**: P0 기능 완성
- **V1**: GitHub OAuth, SEO 탭, 템플릿 확장
- **V2**: 자동 수집, API 발행, 크롬 확장

## 📝 라이선스

MIT

