#!/bin/bash

# Devshiplog Backend 실행 스크립트

echo "🚀 Devshiplog Backend 시작 중..."

# 가상환경 활성화 확인
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. 먼저 python -m venv venv를 실행하세요."
    exit 1
fi

source venv/bin/activate

# PYTHONPATH 설정 (src 디렉토리를 포함)
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# 의존성 확인
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt 파일이 없습니다."
    exit 1
fi

echo "📦 의존성 확인 중..."
pip install -q -r requirements.txt

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 참고하여 생성하세요."
    echo "계속 진행합니다..."
fi

# 데이터베이스 연결 확인
echo "🔍 데이터베이스 연결 확인 중..."
python -c "
import sys
sys.path.insert(0, 'src')
from infrastructure.config.settings import settings
try:
    from sqlalchemy import create_engine
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print('✅ 데이터베이스 연결 성공')
except Exception as e:
    print(f'❌ 데이터베이스 연결 실패: {e}')
    sys.exit(1)
" || exit 1

# Redis 연결 확인
echo "🔍 Redis 연결 확인 중..."
python -c "
import sys
sys.path.insert(0, 'src')
from infrastructure.config.settings import settings
import redis
try:
    r = redis.from_url(settings.REDIS_URL)
    r.ping()
    print('✅ Redis 연결 성공')
except Exception as e:
    print(f'❌ Redis 연결 실패: {e}')
    print('Redis를 실행하세요: brew services start redis 또는 docker run -d -p 6379:6379 redis')
    sys.exit(1)
" || exit 1

# 서버 실행
echo "🌐 FastAPI 서버 시작 중..."
cd src
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn main:app --reload --host 0.0.0.0 --port 8000

