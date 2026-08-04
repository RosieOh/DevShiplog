from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.infrastructure.config.settings import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    # SQL 에코는 디버깅용이라 개발 환경에서만 켠다.
    echo=settings.DEBUG and not settings.is_production,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Iterator[Session]:
    """요청 스코프 DB 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
