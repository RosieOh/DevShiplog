# 구현 현황

> 이 문서는 "무엇이 실제로 동작하는지"를 기록합니다.
> 파일이 존재한다는 것과 기능이 동작한다는 것은 다르므로, 검증 방법을 함께 적습니다.

## ✅ 동작이 검증된 것

| 영역 | 검증 방법 |
|---|---|
| FastAPI 기동 / 라우팅 | `uvicorn src.main:app` + `pytest` |
| 회원가입 / 로그인 / JWT | `tests/test_auth_api.py` |
| 인증 · 소유권 검사 | `tests/test_drafts_api.py` |
| 자동저장 ↔ 버전 스냅샷 분리 | `tests/test_drafts_api.py` |
| 월간 사용량 쿼터 | `tests/test_quota.py` |
| SSRF 방어 | `tests/test_net_guard.py` |
| 민감정보 스캐너 | `tests/test_safety_scanner.py` |
| DB 스키마 마이그레이션 | `alembic upgrade head` |
| Celery Task 등록 | `celery -A src.infrastructure.queue.celery_app inspect registered` |
| Frontend 빌드 / 타입 | `npm run type-check && npm run build` |

## ⚠️ 코드는 완성됐지만 실환경 검증이 필요한 것

아래는 외부 의존성(OpenAI API, 실제 블로그, MariaDB)이 있어야 확인할 수 있습니다.

- **Draft 생성 파이프라인** (outline → 본문 스트리밍 → 스타일 적용)
  - 실제 OpenAI 키로 1건 생성해 보고, `usage_logs` 테이블에 행이 쌓이는지 확인하세요.
- **SSE 실시간 스트리밍**
  - `/drafts/new` 에서 생성 시 본문이 조금씩 채워지는지 확인하세요.
  - 스트림이 실패하더라도 2초 폴링이 최종 상태를 잡아주도록 되어 있습니다.
- **Style DNA 분석**
  - RSS/Atom 이 공개된 블로그로 확인하세요. 피드가 없으면 실패 상태와 사유가 표시됩니다.
- **MariaDB 방언**
  - 테스트는 SQLite 로 돌기 때문에 JSON 컬럼 동작 등은 실제 MariaDB 로 한 번 확인이 필요합니다.

## 🚧 의도적으로 남겨둔 것

- **도메인 엔티티 / 매퍼 분리**
  - 현재 Port 는 SQLAlchemy 모델을 반환합니다. 다만 enum 은 `src/domain/enums.py` 로
    분리했고 Port 는 `TYPE_CHECKING` 으로만 infrastructure 를 참조하므로
    **런타임 의존성 방향은 올바릅니다.**
  - 완전한 엔티티/매퍼 도입은 8개 애그리거트를 모두 건드리는 큰 작업이라
    별도 작업으로 분리했습니다.
- **GitHub OAuth**: V1 범위
- **S3 업로드**: `content_ref` 컬럼만 준비되어 있고 실제 업로드는 미구현
- **SEO 탭 / 발행 연동**: V1~V2 범위

## 🔁 API 변경 메모 (기존 클라이언트 주의)

- `PUT /api/v1/drafts/{id}/version` → **삭제됨**.
  자동저장은 `PUT /drafts/{id}/content`, 스냅샷은 `POST /drafts/{id}/versions` 를 씁니다.
- `GET /api/v1/export/drafts/{id}/export/md` → `GET /api/v1/export/drafts/{id}/md`,
  인증 필수가 되었습니다.
- 요청 본문에서 `user_id` 를 받던 엔드포인트는 모두 JWT 에서 사용자를 식별합니다.
- Draft 생성/변형은 이제 `202 Accepted` 를 반환합니다.

## 🚀 실행 방법

모든 백엔드 명령은 `backend/` 에서 실행합니다.

```bash
# 의존성
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 환경 변수
cp .env.example .env   # OPENAI_API_KEY 등을 채웁니다

# 인프라 + 스키마
docker-compose up -d          # 저장소 루트에서
alembic upgrade head

# 서버 / 워커
uvicorn src.main:app --reload --port 8000
celery -A src.infrastructure.queue.celery_app worker --loglevel=info  # Windows: --pool=solo
```

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```
