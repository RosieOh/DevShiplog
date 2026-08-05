# E2E 검증

앱·DB·Redis·MinIO·Mailpit 을 모두 띄운 뒤 실제 HTTP 로 두드린다.
유닛 테스트가 SQLite 와 가짜 저장소로 도는 반면, 여기서는 실제 구성으로 돈다.

## 돌리는 법

```bash
docker compose up -d
(cd backend && alembic upgrade head && uvicorn src.main:app --port 8000 &)
(cd frontend && npm run build && npm start &)

E2E_API=http://localhost:8000 E2E_WEB=http://localhost:3000 python e2e/platform_e2e.py
E2E_API=http://localhost:8000 E2E_WEB=http://localhost:3000 python e2e/features_e2e.py
E2E_API=http://localhost:8000 E2E_WEB=http://localhost:3000 python e2e/improve_e2e.py

cd e2e/browser && npm ci
CHROME_PATH=$(which chrome) E2E_WEB=http://localhost:3000 node features_ui.mjs
```

## 무엇을 보는가

| 파일 | 범위 |
|---|---|
| `platform_e2e.py` | 발행 → 공개 주소 → SEO 표면 → 소셜 → 비공개 처리 |
| `features_e2e.py` | 업로드, 피드 탭·기간, 목차, 커버 이미지 |
| `improve_e2e.py` | 리사이징·정리, 검색, 시리즈, 조회수, 재설정, 충돌, 알림 SSE |
| `browser/features_ui.mjs` | 탭·목차 스크롤스파이·플로팅 바·업로드 UI |
| `browser/improve_ui.mjs` | 하이라이팅 대비, 시리즈 네비, 재설정 화면, 붙여넣기 업로드, 충돌 배너 |
| `browser/check.mjs` | 대비·가로 오버플로·터치 타깃을 3개 뷰포트에서 |

## 주의

브라우저 스크립트는 실행할 때마다 자기 데이터를 만든다.
DB 에 남아 있는 다른 실행의 글에 기대면, 그 글이 지워지는 순간 깨진다.
