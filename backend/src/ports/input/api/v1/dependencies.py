from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.infrastructure.auth.jwt_handler import decode_access_token
from src.infrastructure.database.repositories.draft_repository_impl import DraftRepositoryImpl
from src.infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl
from src.infrastructure.database.repositories.risk_finding_repository_impl import (
    RiskFindingRepositoryImpl,
)
from src.infrastructure.database.repositories.source_repository_impl import SourceRepositoryImpl
from src.infrastructure.database.repositories.style_profile_repository_impl import (
    StyleProfileRepositoryImpl,
)
from src.infrastructure.database.repositories.usage_log_repository_impl import (
    UsageLogRepositoryImpl,
)
from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from src.infrastructure.database.session import get_db
from src.infrastructure.external.crawler.crawler_service_impl import CrawlerServiceImpl

# auto_error=False 로 두어야 인증 누락 시 우리가 통일된 401 을 낼 수 있다.
security = HTTPBearer(auto_error=False)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="인증이 필요합니다.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _user_id_from_token(token: Optional[str]) -> str:
    if not token:
        raise CREDENTIALS_EXCEPTION
    payload = decode_access_token(token)
    if not payload:
        raise CREDENTIALS_EXCEPTION
    user_id = payload.get("sub")
    if not user_id or not isinstance(user_id, str):
        raise CREDENTIALS_EXCEPTION
    return user_id


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Authorization: Bearer <token> 에서 사용자 ID 를 얻는다."""
    return _user_id_from_token(credentials.credentials if credentials else None)


def get_current_user_id_sse(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = Query(
        default=None,
        description="EventSource 는 헤더를 붙일 수 없어 쿼리 파라미터로 토큰을 받는다.",
    ),
) -> str:
    """SSE 전용 인증.

    브라우저의 EventSource 는 커스텀 헤더를 보낼 수 없다. 그래서 액세스 토큰을
    쿼리 파라미터로도 받는다. 쿼리 토큰은 서버 로그에 남을 수 있으므로
    SSE 엔드포인트에서만 허용한다.
    """
    if credentials and credentials.credentials:
        return _user_id_from_token(credentials.credentials)
    return _user_id_from_token(token)


# --------------------------------------------------------------- repositories


def get_user_repo(db: Session = Depends(get_db)) -> UserRepositoryImpl:
    return UserRepositoryImpl(db)


def get_style_profile_repo(db: Session = Depends(get_db)) -> StyleProfileRepositoryImpl:
    return StyleProfileRepositoryImpl(db)


def get_source_repo(db: Session = Depends(get_db)) -> SourceRepositoryImpl:
    return SourceRepositoryImpl(db)


def get_draft_repo(db: Session = Depends(get_db)) -> DraftRepositoryImpl:
    return DraftRepositoryImpl(db)


def get_job_repo(db: Session = Depends(get_db)) -> JobRepositoryImpl:
    return JobRepositoryImpl(db)


def get_risk_finding_repo(db: Session = Depends(get_db)) -> RiskFindingRepositoryImpl:
    return RiskFindingRepositoryImpl(db)


def get_usage_log_repo(db: Session = Depends(get_db)) -> UsageLogRepositoryImpl:
    return UsageLogRepositoryImpl(db)


# ------------------------------------------------------------------- services


def get_crawler_service() -> CrawlerServiceImpl:
    return CrawlerServiceImpl()
