#!/bin/bash

# 데이터베이스 마이그레이션 스크립트

echo "🗄️  데이터베이스 마이그레이션 시작..."

# 가상환경 활성화
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. 먼저 python -m venv venv를 실행하세요."
    exit 1
fi

source venv/bin/activate

# PYTHONPATH 설정 (src 디렉토리를 포함)
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 참고하여 생성하세요."
fi

# alembic 명령어 실행 (backend 디렉토리에서 실행)
echo "📝 마이그레이션 실행 중..."
alembic upgrade head

echo "✅ 마이그레이션 완료!"

