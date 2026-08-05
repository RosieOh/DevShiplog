#!/bin/bash

# Celery Worker 실행 스크립트

echo "🔄 Celery Worker 시작 중..."

# 가상환경 활성화
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다."
    exit 1
fi

source venv/bin/activate

# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

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
    sys.exit(1)
" || exit 1

# Celery Worker 실행
echo "👷 Celery Worker 시작 중..."
cd src
celery -A infrastructure.queue.celery_app worker --loglevel=info

