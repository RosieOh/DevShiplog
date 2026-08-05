# 문서 작성 기능 개선 제안서

## 개요
현재 구현된 MVP 기능을 기반으로, 문서 작성 워크플로우를 더욱 효율적으로 만들기 위한 추가 기능 제안서입니다.

---

## 1. 초안 생성 전 개요/목차 미리보기 (P1 - 높은 우선순위)

### 목적
초안 생성 전에 목차와 개요를 미리 확인하여 사용자가 원하는 방향으로 조정할 수 있도록 함

### 기능 상세
- **목차 생성 API**: 소스 추출 후, 실제 본문 생성 전에 목차만 먼저 생성
- **목차 편집**: 생성된 목차를 사용자가 직접 수정 가능
- **목차 기반 생성**: 편집된 목차를 기반으로 본문 생성

### 구현 포인트
```typescript
// API
POST /api/v1/drafts/{draft_id}/outline
GET /api/v1/drafts/{draft_id}/outline
PUT /api/v1/drafts/{draft_id}/outline

// UI
- 소스 추출 후 "목차 미리보기" 버튼 표시
- 목차 편집 모달/패널
- 목차 항목 추가/삭제/순서 변경
- 목차 기반으로 "초안 생성" 버튼 활성화
```

### 사용자 시나리오
1. 소스 추출 완료
2. "목차 미리보기" 클릭
3. AI가 생성한 목차 확인 및 수정
4. 수정된 목차로 초안 생성 시작

---

## 2. 초안 생성 진행률 상세 표시 (P1)

### 목적
초안 생성 과정을 단계별로 시각화하여 사용자에게 명확한 피드백 제공

### 기능 상세
- **단계별 진행률**: Ingest → Outline → Draft → Style Apply → Safety Scan → Final Polish
- **각 단계별 예상 시간 표시**
- **현재 단계 하이라이트**
- **완료된 단계 체크 표시**

### 구현 포인트
```typescript
// Job 상태에 단계 정보 추가
interface JobStatus {
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  progress: number
  current_step: 'ingest' | 'outline' | 'draft' | 'style' | 'safety' | 'polish'
  steps: {
    ingest: { status: 'pending' | 'running' | 'completed', progress: number }
    outline: { status: 'pending' | 'running' | 'completed', progress: number }
    // ...
  }
}

// UI
- 진행률 바 (전체)
- 단계별 진행률 카드
- 현재 단계 하이라이트
- 예상 남은 시간 표시
```

---

## 3. 초안 생성 히스토리/로그 (P2)

### 목적
생성된 초안의 출처와 생성 과정을 추적하여 투명성 확보

### 기능 상세
- **생성 로그**: 어떤 소스에서 어떤 정보를 추출했는지 기록
- **생성 파라미터**: 타입, 대상 독자, 길이, Style DNA 사용 여부 등
- **생성 시간 및 소요 시간**
- **사용된 모델 정보** (비용 추적용)

### 구현 포인트
```typescript
// Draft 모델에 추가
interface Draft {
  // ...
  generation_log?: {
    sources: Array<{ id: string, url?: string, title: string }>
    parameters: {
      type: string
      audience: string
      length: string
      style_profile_id?: string
    }
    created_at: string
    duration_seconds: number
    model_used: string
    tokens_used: { prompt: number, completion: number }
  }
}

// UI
- Draft 상세 페이지에 "생성 정보" 탭 추가
- 소스 링크 표시
- 생성 파라미터 표시
- 비용 정보 표시 (유료 플랜)
```

---

## 4. 초안 태그/카테고리 관리 (P2)

### 목적
Draft를 주제별로 분류하여 관리 효율성 향상

### 기능 상세
- **태그 추가/삭제**: Draft에 태그를 추가하여 분류
- **태그별 필터링**: Dashboard에서 태그로 필터링
- **자동 태그 추천**: AI가 초안 내용을 분석하여 태그 추천
- **태그 통계**: 태그별 Draft 개수 표시

### 구현 포인트
```typescript
// Draft 모델에 추가
interface Draft {
  tags?: string[]
}

// API
PUT /api/v1/drafts/{draft_id}/tags
GET /api/v1/tags (모든 태그 목록)

// UI
- Draft 편집 페이지에 태그 입력 필드
- Dashboard에 태그 필터 추가
- 태그 클라우드 표시
```

---

## 5. 초안 노트/메모 기능 (P2)

### 목적
Draft에 개인 메모나 리마인더를 추가하여 협업 및 후속 작업 관리

### 기능 상세
- **Draft별 메모**: 각 Draft에 메모 추가/수정
- **버전별 메모**: 특정 버전에 대한 메모
- **체크리스트**: 발행 전 체크리스트 항목 추가
- **메모 검색**: 메모 내용으로 Draft 검색

### 구현 포인트
```typescript
// Draft 모델에 추가
interface Draft {
  notes?: string
  checklist?: Array<{ id: string, text: string, checked: boolean }>
}

// UI
- Draft 편집 페이지에 "메모" 섹션 추가
- 체크리스트 UI 컴포넌트
- 메모 검색 기능
```

---

## 6. 초안 비교 (Diff View) (P2)

### 목적
버전 간 변경사항을 시각적으로 비교하여 변경 이력을 추적

### 기능 상세
- **버전 비교**: 두 버전을 나란히 비교
- **변경사항 하이라이트**: 추가/삭제/수정된 부분 표시
- **통계**: 단어 수, 줄 수, 변경 비율 등
- **변경사항 요약**: AI가 변경사항을 요약

### 구현 포인트
```typescript
// API
GET /api/v1/drafts/{draft_id}/compare?version1={v1}&version2={v2}

// UI
- 버전 선택 드롭다운 (2개)
- 나란히 비교 뷰
- 변경사항 하이라이트 (추가: 녹색, 삭제: 빨간색)
- 통계 패널
```

---

## 7. 초안 템플릿 저장/불러오기 (P3)

### 목적
자주 사용하는 설정을 템플릿으로 저장하여 재사용

### 기능 상세
- **템플릿 저장**: Draft 생성 옵션(타입, 대상, 길이, Style DNA)을 템플릿으로 저장
- **템플릿 목록**: 저장된 템플릿 목록 표시
- **템플릿 불러오기**: 템플릿을 선택하여 옵션 자동 설정
- **템플릿 공유**: 팀 내 템플릿 공유 (V1 이후)

### 구현 포인트
```typescript
// API
POST /api/v1/templates
GET /api/v1/templates
GET /api/v1/templates/{id}
DELETE /api/v1/templates/{id}

// Template 모델
interface Template {
  id: string
  name: string
  type: string
  audience: string
  length: string
  style_profile_id?: string
  created_at: string
}

// UI
- "템플릿으로 저장" 버튼 (Draft 생성 페이지)
- 템플릿 선택 드롭다운
- 템플릿 관리 페이지
```

---

## 8. 초안 발행 일정 관리 (P3)

### 목적
초안을 특정 날짜/시간에 자동으로 발행하도록 예약

### 기능 상세
- **발행 일정 설정**: 날짜/시간 선택
- **발행 플랫폼 선택**: WordPress, Notion 등 (V1 이후)
- **일정 목록**: 예약된 발행 일정 목록
- **일정 수정/취소**: 발행 전 일정 변경 가능

### 구현 포인트
```typescript
// API
POST /api/v1/drafts/{draft_id}/schedule
GET /api/v1/schedules
PUT /api/v1/schedules/{id}
DELETE /api/v1/schedules/{id}

// Schedule 모델
interface Schedule {
  id: string
  draft_id: string
  platform: 'wordpress' | 'notion' | 'medium'
  scheduled_at: string
  status: 'pending' | 'completed' | 'failed'
}

// UI
- "발행 예약" 버튼 (Export 탭)
- 일정 캘린더 뷰
- 일정 목록 페이지
```

---

## 9. 초안 통계/분석 (P3)

### 목적
작성한 초안에 대한 통계를 제공하여 작성 패턴 파악

### 기능 상세
- **Draft 통계**: 총 Draft 수, 타입별 분포, 평균 길이 등
- **작성 패턴**: 가장 많이 사용하는 타입, 대상 독자 등
- **생성 시간대 분석**: 언제 가장 많이 생성하는지
- **Style DNA 활용도**: Style DNA를 사용한 Draft 비율

### 구현 포인트
```typescript
// API
GET /api/v1/analytics/drafts
GET /api/v1/analytics/writing-patterns
GET /api/v1/analytics/time-distribution

// UI
- Dashboard에 "통계" 섹션 추가
- 차트/그래프 표시 (Chart.js 또는 Recharts)
- 월별/주별 통계
```

---

## 10. 초안 공유 및 협업 (V1 이후)

### 목적
팀 내에서 초안을 공유하고 리뷰할 수 있도록 함

### 기능 상세
- **초안 공유**: 링크 생성 또는 팀원 초대
- **댓글 기능**: 초안에 댓글 추가
- **리뷰 요청**: 특정 팀원에게 리뷰 요청
- **변경사항 알림**: 초안이 수정되면 알림

### 구현 포인트
```typescript
// API
POST /api/v1/drafts/{draft_id}/share
GET /api/v1/drafts/{draft_id}/comments
POST /api/v1/drafts/{draft_id}/comments
POST /api/v1/drafts/{draft_id}/review-request

// UI
- "공유" 버튼
- 댓글 패널
- 리뷰 요청 모달
```

---

## 우선순위 요약

### P1 (즉시 구현 권장)
1. ✅ 초안 생성 전 목차/개요 미리보기
2. ✅ 초안 생성 진행률 상세 표시

### P2 (MVP 완성 후)
3. ✅ 초안 생성 히스토리/로그
4. ✅ 초안 태그/카테고리 관리
5. ✅ 초안 노트/메모 기능
6. ✅ 초안 비교 (Diff View)

### P3 (V1 이후)
7. ✅ 초안 템플릿 저장/불러오기
8. ✅ 초안 발행 일정 관리
9. ✅ 초안 통계/분석
10. ✅ 초안 공유 및 협업

---

## 구현 시 고려사항

### 기술적 고려사항
- **성능**: 목차 미리보기 기능은 별도 API로 분리하여 본문 생성과 독립적으로 동작
- **비용**: 목차만 생성하는 것은 본문 생성보다 저렴하므로 비용 절감 효과
- **UX**: 진행률 표시는 사용자 경험에 큰 영향을 미치므로 우선 구현 권장

### 데이터베이스 스키마
- `drafts` 테이블에 `tags`, `notes`, `checklist` 컬럼 추가 (JSON)
- `templates` 테이블 신규 생성
- `schedules` 테이블 신규 생성
- `draft_comments` 테이블 신규 생성 (V1 이후)

### API 설계
- RESTful API 원칙 준수
- 기존 API와 일관성 유지
- 인증/권한 체크 필수

---

## 결론

문서 작성 워크플로우를 개선하기 위한 10가지 기능을 제안했습니다. 특히 **목차 미리보기**와 **진행률 상세 표시**는 사용자 경험에 큰 영향을 미치므로 우선 구현을 권장합니다.

이 기능들은 MVP의 핵심 기능을 보완하여 더욱 완성도 높은 문서 작성 플랫폼을 만드는 데 기여할 것입니다.

