# Devshiplog Backend

FastAPI 기반 백엔드 서버 실행 가이드

## 사전 요구사항

- Python 3.10 이상
- MariaDB (또는 MySQL)
- Redis
- OpenAI API Key (또는 Anthropic API Key)

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
cd backend
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`backend/.env` 파일을 생성하고 다음 내용을 입력하세요:

```env
# Database
DATABASE_URL=mysql+pymysql://root:1234@localhost:3306/devshiplog

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM APIs
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# AWS S3 (선택사항)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=
AWS_REGION=ap-northeast-2

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]

# App
ENVIRONMENT=development
DEBUG=True
```

### 4. 데이터베이스 설정

#### MariaDB 데이터베이스 생성

```sql
CREATE DATABASE devshiplog CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**참고**: 기본 설정은 `root` 사용자와 비밀번호 `1234`를 사용합니다. 
다른 사용자를 사용하려면 `.env` 파일의 `DATABASE_URL`을 수정하세요.

#### 데이터베이스 마이그레이션

**방법 1: Alembic 사용 (권장)**

```bash
# backend 디렉토리에서 실행해야 합니다 (alembic.ini가 있는 위치)
cd backend

# 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"

# 마이그레이션 실행
alembic upgrade head
```

**방법 2: 직접 테이블 생성 (빠른 방법)**

```bash
cd backend
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python create_tables.py
```

**주의**: `backend/src`가 아닌 `backend` 디렉토리에서 실행해야 합니다!

### 5. Redis 실행

```bash
# macOS (Homebrew)
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

### 6. 서버 실행

#### 개발 모드 (FastAPI 서버만)

```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

또는:

```bash
cd src
python main.py
```

#### 프로덕션 모드 (Celery Worker 포함)

**터미널 1: FastAPI 서버**
```bash
cd src
uvicorn main:app --host 0.0.0.0 --port 8000
```

**터미널 2: Celery Worker**
```bash
cd src
celery -A infrastructure.queue.celery_app worker --loglevel=info
```

**터미널 3: Celery Beat (스케줄링이 필요한 경우)**
```bash
cd src
celery -A infrastructure.queue.celery_app beat --loglevel=info
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 주요 엔드포인트

- `GET /` - API 정보
- `GET /health` - 헬스 체크
- `POST /api/v1/auth/register` - 회원가입
- `POST /api/v1/auth/login` - 로그인
- `GET /api/v1/drafts` - Draft 목록
- `POST /api/v1/drafts` - Draft 생성
- `GET /api/v1/jobs/{job_id}` - Job 상태 조회
- `GET /api/v1/jobs/{job_id}/stream` - Job 스트리밍 (SSE)

## 문제 해결

### 데이터베이스 연결 오류

- MariaDB가 실행 중인지 확인: `mysql -u devshiplog -p`
- `.env` 파일의 `DATABASE_URL` 확인
- 데이터베이스와 사용자가 생성되었는지 확인

### Redis 연결 오류

- Redis가 실행 중인지 확인: `redis-cli ping`
- `.env` 파일의 `REDIS_URL` 확인

### Celery Worker 오류

- Redis가 실행 중인지 확인
- `PYTHONPATH` 설정 확인: `export PYTHONPATH="${PYTHONPATH}:/path/to/backend/src"`

## 개발 팁

### 환경 변수 확인

```python
from infrastructure.config.settings import settings
print(settings.DATABASE_URL)
```

### 데이터베이스 모델 확인

```python
from infrastructure.database.models import *
# 모델 확인
```

### Celery Task 테스트

```python
from infrastructure.queue.tasks.draft_generation_tasks import generate_draft_task
# Task 직접 호출 테스트
```

