# 운영

공개 서비스로 열기 전에 있어야 하는 것들. 기능이 아니라 **사고가 났을 때 쓸 수 있는가**의 문제다.

---

## 1. 운영자

### 권한

`users.role` 은 `user` 또는 `admin` 이다. 역할을 세분화하지 않았다 — 쓰는 사람이 하나인데
역할을 셋으로 나누면 관리만 늘고 얻는 게 없다.

승격은 **서버에서만** 한다. 운영자를 만드는 버튼이 웹에 있으면 그 버튼 자체가 공격 표면이다.

```bash
cd backend
python -m scripts.grant_admin someone@example.com          # 지정
python -m scripts.grant_admin someone@example.com --revoke # 회수
python -m scripts.grant_admin --list                       # 현재 운영자
```

마지막 운영자는 회수되지 않는다. 스스로 잠기면 신고를 볼 사람이 아무도 없어진다.

### 화면

| 주소 | 무엇 |
|---|---|
| `/admin` | 밀린 신고 수, 최근 서버 오류, 의존성 상태 |
| `/admin/reports` | 신고 처리 |

권한이 없으면 **404** 로 답한다. 403 은 "그런 화면이 있긴 하다"를 알려주는 셈이라
운영자 화면의 존재를 굳이 광고하지 않는다. 프론트엔드의 판정은 표시용일 뿐이고,
권한은 서버가 매 요청 다시 확인한다.

### 신고 처리

세 가지 결정만 있다.

- **문제 없음** — 신고를 반려한다 (`rejected`)
- **조치함 (글은 유지)** — 신고는 타당했지만 글은 그대로 둔다
- **글 내리기** — 글을 비공개(`unlisted`)로 바꾼다. **지우지 않으므로 오판이면 되돌릴 수 있다**

신고 목록에는 대상 글의 제목·작성자·본문 앞부분이 함께 온다. 신고만 보고 대상을 다시
찾아 들어가야 하면 처리가 느려지고, 느려지면 안 하게 된다.

사용자 정지는 아직 없다. 되돌리기가 훨씬 어렵고, 지금 규모에서 필요하지 않다.

---

## 2. 관측

### 요청 추적

모든 응답에 `X-Request-ID` 가 붙는다. 앞단(프록시·로드밸런서)이 이미 `X-Request-ID` 를
붙였으면 그 값을 그대로 쓴다 — 새로 만들면 프록시 로그와 앱 로그를 이을 수 없다.

500 응답에는 `request_id` 와 `error_id` 가 실린다. 사용자가 "오류가 났어요"라고만 말하면
로그에서 그 요청을 찾을 방법이 없기 때문이다.

### 로그

```bash
LOG_JSON=true   # 배포. 한 줄에 하나의 JSON 객체
LOG_JSON=false  # 개발. 사람이 읽는 형식 (기본)
```

배포에서 JSON 을 쓰는 이유는 검색이다. 개발에서 JSON 을 읽히면 로그를 안 보게 되고,
안 보는 로그는 없는 것과 같다.

접근 로그에는 `duration_ms` 가 있다. uvicorn 기본 접근 로그에는 소요 시간이 없어서
"느리다"는 신고를 받았을 때 확인할 수 있는 게 없다.

### 오류

처리되지 않은 예외는 프로세스 안에 **지문별로 묶여** 쌓이고 `/admin` 에서 보인다.
한 건씩 쌓으면 같은 오류가 1000번 나는 순간 화면이 그것만으로 가득 차서
무엇부터 고칠지 알 수 없다.

**이 수집기의 한계는 분명하다.** 메모리에만 있으므로 재시작하면 사라지고, 워커가 여럿이면
요청이 닿은 워커의 것만 보인다. 화면에도 이 문장을 적어 두었다 — 모르고 믿는 게
없는 것보다 나쁘다.

영구 보관이 필요하면 `SENTRY_DSN` 을 설정한다. 없어도 서비스는 그대로 돈다.
1인 개발 단계에서 외부 서비스 가입을 전제로 하면 결국 아무것도 안 붙이고 넘어가게 된다.

```bash
pip install sentry-sdk
SENTRY_DSN=https://...@sentry.io/...
```

### 헬스체크

| 경로 | 용도 | 하는 일 |
|---|---|---|
| `/health` | 재시작 판단 (liveness) | 아무것도 두드리지 않는다 |
| `/health/ready` | 트래픽 투입 판단 (readiness) | DB·Redis·저장소를 실제로 두드린다 |

`{"status":"healthy"}` 만 답하는 헬스체크는 프로세스가 살아있다는 것만 말한다.
DB 가 끊겨도 healthy 라고 답하고, 로드밸런서는 죽은 인스턴스로 트래픽을 계속 보낸다.

Redis 는 **필수가 아니다**. 레이트리밋과 캐시 무효화가 쓰지만 끊겨도 글 읽기·쓰기는 된다.
필수로 두면 Redis 재시작 때 서비스 전체가 트래픽에서 빠진다 — 실제로는 조금 불편해질 뿐인데.

준비되지 않았으면 **503** 을 낸다.

---

## 3. 백업

> 볼륨은 백업이 아니다. 잘못된 `DELETE` 는 볼륨에도 그대로 반영된다.
> 그리고 **복원해 본 적 없는 백업은 백업이 아니라 희망이다.**

### 뜨기

```bash
cd backend
python -m scripts.backup                          # ./backups/<UTC시각>/
python -m scripts.backup --out /mnt/backups
python -m scripts.backup --container devshiplog-db  # mariadb-dump 가 로컬에 없을 때
```

받는 것:

- `database.sql.gz` — 논리 덤프 (`--single-transaction` 이라 서비스를 멈추지 않는다)
- `objects/` — 업로드된 파일. **DB 만 되살리면 모든 글의 이미지가 깨진 채로 돌아온다**
- `manifest.json` — 시각, 앱 버전, 스키마 리비전, 덤프 SHA-256, **표 별 행 수**

행 수를 적어 두지 않으면 복원 결과가 맞는지 확인할 방법이 없다.

보존 기간이 지난 백업은 자동으로 지운다 (`BACKUP_RETENTION_DAYS`, 기본 14일).
보존 기간이 없으면 디스크가 찰 때까지 쌓이고, 디스크가 차면 서비스가 멈춘다.

### 검증 — 이게 본체다

```bash
BACKUP_ADMIN_USER=root BACKUP_ADMIN_PASSWORD=... \
  python -m scripts.verify_backup --latest
```

임시 DB 를 만들어 **실제로 복원해 보고**, 표 별 행 수를 기록과 맞춘 뒤 지운다.
운영 DB 는 건드리지 않는다. 덤프가 잘렸으면 SHA-256 에서 먼저 걸린다.

실측 결과 (2026-08-06, 개발 DB):

```
검증 통과 — 27개 표 2,710행이 그대로 되살아납니다.
```

일부러 잘라 본 덤프:

```
덤프가 손상되었습니다. 이 백업은 쓸 수 없습니다.
  기록: a8f1d949...  실제: 8ea051c5...     (exit 1)
```

CI 의 `backup` 잡이 매번 이 왕복을 돌린다. 스크립트가 조용히 망가지는 것을 막는 유일한 방법이다.

### 되돌리기

```bash
# 안전: 다른 이름으로 복원해서 확인부터
python -m scripts.restore ./backups/20260806T145944Z --into devshiplog_restored

# 실제 복구: 쓰고 있는 DB 를 덮어쓴다 (--yes 없이는 실행되지 않는다)
python -m scripts.restore ./backups/20260806T145944Z --into devshiplog --yes --objects
```

운영 DB 를 덮어쓸 때 확인을 요구하는 이유는 하나다 — 장애 한복판에서 손이 미끄러진다.

복원 후 스키마 리비전(`manifest.json` 의 `alembic_revision`)이 지금 코드보다 낮으면
`alembic upgrade head` 를 이어서 돌린다.

### 자동화

```cron
# 매일 04:00 백업, 04:30 검증. 검증 실패는 메일로 온다 (cron 기본 동작).
0 4 * * *  cd /srv/devshiplog/backend && ./venv/bin/python -m scripts.backup >> /var/log/devshiplog-backup.log 2>&1
30 4 * * * cd /srv/devshiplog/backend && ./venv/bin/python -m scripts.verify_backup --latest >> /var/log/devshiplog-backup.log 2>&1
```

백업만 걸고 검증을 안 걸면, 정작 필요한 날에 "덤프가 비어 있었다"를 처음 알게 된다.

백업 파일은 **다른 기계로 옮겨야 한다.** 같은 디스크에 둔 백업은 디스크가 죽는 순간 함께 죽는다.

### 설정

| 변수 | 기본 | 뜻 |
|---|---|---|
| `BACKUP_DIR` | `./backups` | 보관 위치 |
| `BACKUP_RETENTION_DAYS` | `14` | 보존 기간 (0 이면 안 지움) |
| `BACKUP_DB_CONTAINER` | — | `mariadb-dump` 가 로컬에 없을 때 쓸 컨테이너 |
| `BACKUP_ADMIN_USER` / `BACKUP_ADMIN_PASSWORD` | — | 복원·검증용 DB 생성 권한 계정 |

앱 계정에는 `CREATE DATABASE` 권한이 없다 — 있어서도 안 된다. 그래서 복원과 검증만
관리 계정을 쓴다.

---

## 아직 없는 것

솔직하게 적어 둔다.

- **알림이 없다.** 오류는 `/admin` 에 쌓이지만 아무도 안 보면 모른다. 사람이 늘면
  Sentry 알림이나 서버 헬스 감시를 붙여야 한다.
- **오류 수집기가 프로세스 메모리에 있다.** 워커가 여럿이면 일부만 보인다.
- **백업이 같은 기계에 있다.** 오프사이트 복제는 배포 환경이 정해진 뒤에 붙인다.
- **사용자 정지가 없다.** 지금은 글을 내리는 것까지만 할 수 있다.
