# 구현 가능성 검토 보고서

## ✅ 기술적 구현 가능성: **완전히 가능**

### 1. 기술 스택 호환성

#### 프론트엔드 (Next.js + Tailwind CSS)
- ✅ **Feature-based 아키텍처**: Next.js App Router의 폴더 구조와 완벽 호환
- ✅ **실시간 스트리밍**: Server-Sent Events (SSE) 또는 WebSocket 지원
- ✅ **마크다운 에디터**: Tiptap, React Markdown 등 라이브러리 풍부
- ✅ **OAuth 인증**: NextAuth.js로 GitHub OAuth 구현 가능

#### 백엔드 (FastAPI + Hexagonal Architecture)
- ✅ **Hexagonal Architecture**: FastAPI는 의존성 주입과 레이어 분리가 용이
- ✅ **비동기 처리**: FastAPI의 async/await + Celery/BullMQ 조합
- ✅ **스트리밍 응답**: `StreamingResponse`로 LLM 스트리밍 지원
- ✅ **크롤링**: `httpx`, `beautifulsoup4`, `readability-lxml` 등

#### 데이터베이스 (MariaDB)
- ✅ **JSON 지원**: MariaDB 10.2+ JSON 타입 지원 (style_profiles, extracted_json 등)
- ✅ **트랜잭션**: ACID 보장으로 버전 관리 안정성
- ✅ **인덱싱**: 사용자별 조회 최적화 가능

### 2. 핵심 기능 구현 가능성

#### ✅ F-ING-001: URL 본문 추출
- **구현 방법**: 
  - `readability-lxml` 또는 `trafilatura`로 본문 추출
  - `beautifulsoup4`로 코드 블록/이미지 분리
  - 실패 시 `playwright`/`selenium` 스냅샷 fallback
- **난이도**: 중간 (크롤링 안티봇 우회 필요 시 복잡도 증가)

#### ✅ F-STD-001: Style DNA 생성
- **구현 방법**:
  - RSS 피드 우선 파싱 (feedparser)
  - 공개 페이지 크롤링 (readability)
  - LLM으로 스타일 특징 추출 (종결어미, 문장 길이, 구조 패턴)
  - 통계 기반 규칙 생성 (JSON)
- **난이도**: 중상 (LLM 프롬프트 엔지니어링 필요)

#### ✅ F-DRF-001/002: Draft 생성
- **구현 방법**:
  - LLM 파이프라인: Outline → Draft → Style Apply → Polish
  - 스트리밍: OpenAI/Anthropic 스트리밍 API 활용
  - Job 큐: Celery + Redis로 비동기 처리
- **난이도**: 중간 (LLM 비용 최적화 필요)

#### ✅ F-SAF-001: 민감정보 탐지
- **구현 방법**:
  - 정규식 패턴 매칭 (AWS 키, JWT, 토큰 등)
  - LLM 보조 탐지 (컨텍스트 기반)
  - 위치 추적 (라인 번호, 스니펫)
- **난이도**: 낮음~중간 (패턴 정확도 튜닝 필요)

#### ✅ F-VSN-001: 버전 관리
- **구현 방법**:
  - MariaDB에 `draft_versions` 테이블
  - diff 라이브러리 (`difflib`, `diff-match-patch`)
- **난이도**: 낮음

### 3. 아키텍처 설계 검토

#### Feature-based (프론트엔드)
```
app/
  (features)/
    auth/
    onboarding/
    dashboard/
    drafts/
    style-profiles/
    safety/
    export/
```
- ✅ Next.js App Router와 자연스럽게 매핑
- ✅ 각 feature별 독립적 개발/테스트 가능

#### Hexagonal Architecture (FastAPI)
```
src/
  domain/          # 비즈니스 로직 (순수)
  application/     # 유스케이스
  infrastructure/  # 외부 의존성 (DB, LLM, 크롤링)
  ports/           # 인터페이스 (입력/출력)
```
- ✅ FastAPI의 의존성 주입과 완벽 호환
- ✅ 테스트 용이성 (모킹 쉬움)
- ✅ LLM/크롤링 등 외부 서비스 교체 용이

### 4. 기술적 도전 과제 및 해결 방안

#### 도전 1: 크롤링 안티봇 우회
- **해결**: User-Agent 로테이션, 요청 간격 조절, 필요시 프록시
- **대안**: 공식 API 우선 사용 (GitHub API, Medium RSS 등)

#### 도전 2: LLM 비용 관리
- **해결**: 
  - 모델 라우팅 (gpt-3.5-turbo → 초안, gpt-4 → 리라이트)
  - 토큰 사용량 추적 및 제한
  - 캐싱 (동일 소스 재생성 시)

#### 도전 3: 스트리밍 UX
- **해결**: 
  - FastAPI `StreamingResponse` + SSE
  - 프론트엔드 `EventSource` 또는 `fetch` 스트리밍
  - 부분 렌더링 (마크다운 점진적 파싱)

#### 도전 4: MariaDB JSON 성능
- **해결**: 
  - 자주 조회되는 필드는 별도 컬럼으로 정규화
  - JSON 인덱싱 (MariaDB 10.6+)
  - 필요시 PostgreSQL 마이그레이션 경로 유지

### 5. MVP 구현 우선순위 (기술적 난이도 기준)

#### P0 (4-6주 목표) - 모두 구현 가능
1. ✅ URL/텍스트 입력 → 본문 추출 (2-3일)
2. ✅ Draft 생성 (Job + 스트리밍) (1주)
3. ✅ Style DNA v0 (1주)
4. ✅ 에디터/프리뷰 (3-4일)
5. ✅ Safety scan v0 (3-4일)
6. ✅ 버전 관리 (2일)

#### P1 - 구현 가능
- 변형 기능 (짧게/길게 등) - LLM 재호출
- Draft diff 뷰 - 라이브러리 활용

#### P2 - 구현 가능
- GitHub OAuth - NextAuth.js
- 자동 초안 생성 - 스케줄러 (APScheduler)

### 6. 결론

**✅ 모든 기능이 기술적으로 구현 가능합니다.**

#### 강점
- 선택한 스택이 요구사항에 적합
- Feature-based + Hexagonal 조합이 확장성과 테스트 용이성 제공
- MariaDB도 충분히 사용 가능 (JSON 지원, 성능)

#### 권장사항
1. **MVP 단계**: MariaDB로 시작, 필요시 PostgreSQL 전환 경로 유지
2. **비용 관리**: LLM 호출 추적 시스템을 초기부터 구축
3. **에러 처리**: 크롤링 실패, LLM 타임아웃 등 graceful degradation 필수
4. **모니터링**: Job 상태, 비용, 사용량 대시보드 초기 구축

#### 예상 개발 기간
- **MVP (P0)**: 4-6주 (1인 개발 기준)
- **V1 (P0+P1)**: 추가 2-3주
- **V2 (유료 기능)**: 추가 4-6주

---

**다음 단계**: 프로젝트 구조 및 초기 설정 파일 생성

