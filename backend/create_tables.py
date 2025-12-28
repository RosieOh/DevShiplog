#!/usr/bin/env python3
"""
데이터베이스 테이블 생성 스크립트
SQLAlchemy를 사용하여 모든 테이블을 생성합니다.
"""
import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from infrastructure.database.session import engine, Base
from infrastructure.database.models import (
    user,
    draft,
    draft_version,
    source,
    style_profile,
    job,
    template,
    schedule,
    risk_finding,
    usage_log,
)

def create_tables():
    """모든 테이블 생성"""
    print("Creating all tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)

