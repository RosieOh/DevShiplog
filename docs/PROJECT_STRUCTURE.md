# 프로젝트 구조 설계

## 전체 아키텍처

```
Devshiplog/
├── frontend/              # Next.js (Feature-based)
├── backend/               # FastAPI (Hexagonal)
├── docker-compose.yml     # 로컬 개발 환경
└── README.md
```

## 1. Frontend 구조 (Next.js + Feature-based)

```
frontend/
├── app/                          # Next.js App Router
│   ├── (auth)/
│   │   ├── login/
│   │   └── callback/
│   ├── (features)/
│   │   ├── onboarding/
│   │   │   └── style/
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── drafts/
│   │   │   ├── new/
│   │   │   │   └── page.tsx
│   │   │   └── [id]/
│   │   │       └── edit/
│   │   │           └── page.tsx
│   │   ├── style-profiles/
│   │   │   └── page.tsx
│   │   └── safety/
│   │       └── [draftId]/
│   │           └── page.tsx
│   ├── api/                      # Next.js API Routes (필요시)
│   ├── layout.tsx
│   └── page.tsx                  # Landing
│
├── features/                     # Feature 모듈
│   ├── auth/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   ├── onboarding/
│   │   ├── components/
│   │   │   ├── StyleDNAForm.tsx
│   │   │   └── StyleDNAResult.tsx
│   │   ├── hooks/
│   │   │   └── useStyleDNA.ts
│   │   └── services/
│   │       └── styleDNAService.ts
│   ├── drafts/
│   │   ├── components/
│   │   │   ├── DraftEditor.tsx
│   │   │   ├── DraftPreview.tsx
│   │   │   ├── SourceInput.tsx
│   │   │   └── GenerationOptions.tsx
│   │   ├── hooks/
│   │   │   ├── useDraftGeneration.ts
│   │   │   ├── useDraftStreaming.ts
│   │   │   └── useDraftVersions.ts
│   │   └── services/
│   │       └── draftService.ts
│   ├── style-profiles/
│   ├── safety/
│   │   ├── components/
│   │   │   ├── SafetyScanResults.tsx
│   │   │   └── RiskFindingCard.tsx
│   │   └── services/
│   └── export/
│
├── components/                   # 공통 컴포넌트
│   ├── ui/                      # shadcn/ui 기반
│   ├── layout/
│   └── markdown/
│
├── lib/                         # 유틸리티
│   ├── api/
│   │   └── client.ts            # Axios/Fetch 래퍼
│   ├── utils/
│   └── types/                   # TypeScript 타입
│
├── hooks/                       # 공통 훅
└── styles/
    └── globals.css
```

## 2. Backend 구조 (FastAPI + Hexagonal)

```
backend/
├── src/
│   ├── domain/                  # 비즈니스 로직 (순수)
│   │   ├── entities/
│   │   │   ├── user.py
│   │   │   ├── style_profile.py
│   │   │   ├── source.py
│   │   │   ├── draft.py
│   │   │   └── draft_version.py
│   │   ├── value_objects/
│   │   │   ├── style_rules.py
│   │   │   └── risk_finding.py
│   │   └── services/
│   │       ├── style_analyzer.py
│   │       └── safety_scanner.py
│   │
│   ├── application/             # 유스케이스
│   │   ├── use_cases/
│   │   │   ├── style_profile/
│   │   │   │   ├── create_style_profile.py
│   │   │   │   └── get_style_profile.py
│   │   │   ├── source/
│   │   │   │   ├── extract_url.py
│   │   │   │   └── extract_text.py
│   │   │   ├── draft/
│   │   │   │   ├── create_draft.py
│   │   │   │   ├── transform_draft.py
│   │   │   │   └── get_draft.py
│   │   │   └── safety/
│   │   │       ├── scan_draft.py
│   │   │       └── apply_fix.py
│   │   └── dto/                 # Data Transfer Objects
│   │
│   ├── infrastructure/          # 외부 의존성
│   │   ├── database/
│   │   │   ├── models/          # SQLAlchemy 모델
│   │   │   ├── repositories/    # Repository 구현
│   │   │   └── session.py
│   │   ├── external/
│   │   │   ├── llm/
│   │   │   │   ├── openai_client.py
│   │   │   │   └── anthropic_client.py
│   │   │   ├── crawler/
│   │   │   │   ├── url_extractor.py
│   │   │   │   └── readability_extractor.py
│   │   │   └── storage/
│   │   │       └── s3_client.py
│   │   ├── queue/
│   │   │   ├── celery_app.py
│   │   │   └── tasks/
│   │   │       ├── style_profile_tasks.py
│   │   │       ├── draft_generation_tasks.py
│   │   │       └── safety_scan_tasks.py
│   │   └── config/
│   │       └── settings.py
│   │
│   ├── ports/                   # 인터페이스
│   │   ├── input/               # 입력 포트 (API)
│   │   │   ├── api/
│   │   │   │   ├── v1/
│   │   │   │   │   ├── router.py
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── style_profiles.py
│   │   │   │   │   ├── sources.py
│   │   │   │   │   ├── drafts.py
│   │   │   │   │   ├── jobs.py
│   │   │   │   │   └── safety.py
│   │   │   │   └── dependencies.py
│   │   │   └── schemas/         # Pydantic 스키마
│   │   └── output/              # 출력 포트 (Repository 인터페이스)
│   │       ├── repositories/
│   │       │   ├── user_repository.py
│   │       │   ├── style_profile_repository.py
│   │       │   ├── source_repository.py
│   │       │   └── draft_repository.py
│   │       └── services/
│   │           ├── llm_service.py
│   │           └── crawler_service.py
│   │
│   └── main.py                  # FastAPI 앱 진입점
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── alembic/                     # DB 마이그레이션
├── requirements.txt
└── pyproject.toml
```

## 3. 데이터베이스 스키마 (MariaDB)

```sql
-- users
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);

-- style_profiles
CREATE TABLE style_profiles (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    blog_url VARCHAR(500) NOT NULL,
    sample_count INT DEFAULT 5,
    status ENUM('queued', 'running', 'succeeded', 'failed') DEFAULT 'queued',
    profile_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);

-- sources
CREATE TABLE sources (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    type ENUM('url', 'raw') NOT NULL,
    origin VARCHAR(500),
    title VARCHAR(500),
    content TEXT,
    content_ref VARCHAR(500),  -- S3 key
    extracted_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);

-- drafts
CREATE TABLE drafts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    type VARCHAR(50),
    audience VARCHAR(50),
    length_preset VARCHAR(50),
    style_profile_id VARCHAR(36),
    status ENUM('active', 'archived') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (style_profile_id) REFERENCES style_profiles(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id)
);

-- draft_versions
CREATE TABLE draft_versions (
    id VARCHAR(36) PRIMARY KEY,
    draft_id VARCHAR(36) NOT NULL,
    version_no INT NOT NULL,
    content_md TEXT,
    content_ref VARCHAR(500),  -- S3 key
    meta_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (draft_id) REFERENCES drafts(id) ON DELETE CASCADE,
    INDEX idx_draft_id (draft_id),
    UNIQUE KEY unique_draft_version (draft_id, version_no)
);

-- risk_findings
CREATE TABLE risk_findings (
    id VARCHAR(36) PRIMARY KEY,
    draft_version_id VARCHAR(36) NOT NULL,
    category ENUM('token', 'email', 'phone', 'internal_url', 'company', 'secret') NOT NULL,
    severity ENUM('low', 'med', 'high') DEFAULT 'med',
    snippet TEXT,
    location_json JSON,
    status ENUM('open', 'masked', 'deleted', 'ignored') DEFAULT 'open',
    ignore_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (draft_version_id) REFERENCES draft_versions(id) ON DELETE CASCADE,
    INDEX idx_draft_version_id (draft_version_id),
    INDEX idx_status (status)
);

-- jobs
CREATE TABLE jobs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    type ENUM('extract', 'style', 'draft', 'transform', 'safety') NOT NULL,
    status ENUM('queued', 'running', 'succeeded', 'failed') DEFAULT 'queued',
    progress INT DEFAULT 0,
    result_ref JSON,
    error_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);

-- usage_logs
CREATE TABLE usage_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    job_id VARCHAR(36),
    model_name VARCHAR(100),
    prompt_tokens INT,
    completion_tokens INT,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```

## 4. 의존성 주입 구조 (Hexagonal)

```python
# main.py 예시
from fastapi import FastAPI
from infrastructure.database.session import get_db
from infrastructure.config.settings import Settings
from ports.input.api.v1.router import api_router

app = FastAPI()

# 의존성 주입 설정
def get_repositories():
    db = next(get_db())
    return {
        'user_repo': UserRepository(db),
        'style_profile_repo': StyleProfileRepository(db),
        'draft_repo': DraftRepository(db),
    }

def get_services():
    return {
        'llm_service': OpenAIService(),
        'crawler_service': CrawlerService(),
    }

app.include_router(api_router, dependencies=[Depends(get_repositories), Depends(get_services)])
```

## 5. 비동기 Job 처리 흐름

```
1. API 요청 → Job 생성 (DB)
2. Celery Task 큐에 추가
3. Worker가 Task 처리:
   - URL 크롤링
   - LLM 호출 (스트리밍)
   - 결과 저장
4. WebSocket/SSE로 프론트엔드에 진행 상황 전송
5. 완료 시 Job 상태 업데이트
```

## 6. 환경 변수 구조

```bash
# Backend (.env)
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/devshiplog
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

## 7. 개발 워크플로우

1. **로컬 개발**
   - `docker-compose up` (MariaDB, Redis)
   - Backend: `uvicorn src.main:app --reload`
   - Frontend: `npm run dev`
   - Worker: `celery -A src.infrastructure.queue.celery_app worker`

2. **테스트**
   - Backend: `pytest`
   - Frontend: `npm test`

3. **마이그레이션**
   - `alembic revision --autogenerate -m "description"`
   - `alembic upgrade head`

