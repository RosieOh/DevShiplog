# 개발 가이드

## 아키텍처 개요

### Frontend: Feature-based Architecture

각 기능을 독립적인 모듈로 구성하여 확장성과 유지보수성을 높입니다.

```
features/
  ├── auth/           # 인증 관련
  ├── onboarding/     # 온보딩 (Style DNA 설정)
  ├── drafts/         # Draft 생성/편집
  ├── style-profiles/ # Style DNA 관리
  ├── safety/         # Safety 검사
  └── export/         # Export 기능
```

각 feature는 다음 구조를 가집니다:
- `components/`: UI 컴포넌트
- `hooks/`: 커스텀 훅
- `services/`: API 호출 로직
- `types/`: TypeScript 타입 정의

### Backend: Hexagonal Architecture

비즈니스 로직과 외부 의존성을 분리하여 테스트 용이성과 확장성을 확보합니다.

```
src/
  ├── domain/         # 비즈니스 로직 (순수)
  ├── application/    # 유스케이스
  ├── infrastructure/ # 외부 의존성 (DB, LLM, 크롤링)
  └── ports/          # 인터페이스 (입력/출력)
```

## 개발 워크플로우

### 1. 새로운 Feature 추가 (Frontend)

1. `features/` 하위에 새 폴더 생성
2. `components/`, `hooks/`, `services/` 구조 생성
3. `app/` 하위에 라우트 추가
4. API 클라이언트에 엔드포인트 추가

예시:
```typescript
// features/drafts/services/draftService.ts
import { apiClient } from '@/lib/api/client'

export const draftService = {
  create: async (data: CreateDraftRequest) => {
    return apiClient.post('/api/v1/drafts', data)
  },
  // ...
}
```

### 2. 새로운 Use Case 추가 (Backend)

1. `application/use_cases/` 하위에 유스케이스 파일 생성
2. `ports/output/repositories/`에 인터페이스 정의
3. `infrastructure/database/repositories/`에 구현
4. `ports/input/api/v1/`에 엔드포인트 추가

예시:
```python
# application/use_cases/draft/create_draft.py
from ports.output.repositories.draft_repository import DraftRepository
from ports.output.services.llm_service import LLMService

class CreateDraftUseCase:
    def __init__(
        self,
        draft_repo: DraftRepository,
        llm_service: LLMService,
    ):
        self.draft_repo = draft_repo
        self.llm_service = llm_service
    
    async def execute(self, request: CreateDraftRequest):
        # 비즈니스 로직
        pass
```

### 3. 비동기 Job 처리

1. `src/infrastructure/queue/tasks/`에 Celery Task 정의
2. API에서 Job 생성 후 Task 큐에 추가
3. Worker가 처리하고 결과를 DB에 저장
4. 프론트엔드는 Job 상태를 폴링하거나 SSE로 수신

예시:
```python
# src/infrastructure/queue/tasks/draft_generation_tasks.py
from src.infrastructure.queue.celery_app import celery_app

@celery_app.task
def generate_draft_task(draft_id: str, source_ids: list):
    # LLM 호출 및 Draft 생성
    pass
```

## 코딩 컨벤션

### Frontend (TypeScript)

- 컴포넌트: PascalCase (`DraftEditor.tsx`)
- 훅: camelCase with `use` prefix (`useDraftGeneration.ts`)
- 서비스: camelCase (`draftService.ts`)
- 타입: PascalCase (`DraftResponse`)

### Backend (Python)

- 파일명: snake_case (`create_draft.py`)
- 클래스: PascalCase (`CreateDraftUseCase`)
- 함수/변수: snake_case (`create_draft`)
- 상수: UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`)

## 테스트 전략

### Frontend
- 단위 테스트: Jest + React Testing Library
- E2E 테스트: Playwright (선택)

### Backend
- 단위 테스트: pytest
- 통합 테스트: pytest + testcontainers (선택)

## 환경 변수 관리

### Backend
`.env` 파일을 루트에 생성:
```env
DATABASE_URL=mysql+pymysql://...
REDIS_URL=redis://...
OPENAI_API_KEY=...
```

### Frontend
`.env.local` 파일 생성:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 데이터베이스 마이그레이션

```bash
# 새 마이그레이션 생성
cd backend
alembic revision --autogenerate -m "description"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1
```

## 디버깅

### Backend
- FastAPI 자동 문서: http://localhost:8000/docs
- 로그: `uvicorn`의 `--log-level debug`

### Frontend
- React DevTools
- Next.js 개발 모드: 자동 리로드

#### `Cannot find module './vendor-chunks/*.js'`

**dev 서버가 떠 있는 동안 `npm run build` 를 돌리면 난다.** 둘 다 `.next` 를 쓰는데
빌드가 dev 서버가 물고 있던 청크를 덮어써서, 그 뒤로 모든 페이지가 500 이 된다.
코드는 멀쩡하므로 아무리 들여다봐도 원인이 안 보인다.

```bash
# dev 를 내리고
rm -rf frontend/.next
npx next dev -p 3001
```

빌드로 검증해야 하면 dev 를 먼저 내린다. 둘을 같이 돌리지 않는다.

## 성능 최적화

1. **LLM 호출 최적화**
   - 모델 라우팅 (비용/품질 균형)
   - 캐싱 (동일 소스 재생성)
   - 스트리밍으로 UX 개선

2. **데이터베이스**
   - 인덱스 최적화
   - JSON 필드는 자주 조회되는 값만 별도 컬럼으로

3. **프론트엔드**
   - 코드 스플리팅
   - 이미지 최적화
   - API 호출 최소화 (React Query 등)

## 배포 체크리스트

- [ ] 환경 변수 설정
- [ ] 데이터베이스 마이그레이션
- [ ] Celery Worker 실행
- [ ] Redis 연결 확인
- [ ] LLM API 키 설정
- [ ] S3 버킷 설정 (필요시)
- [ ] CORS 설정 확인
- [ ] 로깅 설정

