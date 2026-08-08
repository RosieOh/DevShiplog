import hashlib
import hmac
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.domain.enums import UserRole
from src.infrastructure.observability.context import user_id_var
from src.infrastructure.auth.jwt_handler import decode_access_token
from src.infrastructure.config.settings import settings
from src.infrastructure.database.repositories.draft_repository_impl import DraftRepositoryImpl
from src.infrastructure.database.repositories.moderation_repository_impl import (
    BlockRepositoryImpl,
    ReportRepositoryImpl,
)
from src.infrastructure.database.repositories.post_repository_impl import PostRepositoryImpl
from src.infrastructure.database.repositories.social_repository_impl import (
    CommentRepositoryImpl,
    FollowRepositoryImpl,
    LikeRepositoryImpl,
    NotificationRepositoryImpl,
)
from src.infrastructure.database.repositories.taxonomy_repository_impl import (
    SeriesRepositoryImpl,
    TagRepositoryImpl,
)
from src.infrastructure.ratelimit.limiter import rate_limiter
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
    # 로그에 누구의 요청인지 남긴다. 오류를 재현하려면 "어떤 상태의 사용자인가" 가 필요하고,
    # 요청 ID 만으로는 거기까지 못 간다.
    user_id_var.set(user_id)
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


# ------------------------------------------------------ 블로그 플랫폼 repositories


def get_post_repo(db: Session = Depends(get_db)) -> PostRepositoryImpl:
    return PostRepositoryImpl(db)


def get_tag_repo(db: Session = Depends(get_db)) -> TagRepositoryImpl:
    return TagRepositoryImpl(db)


def get_series_repo(db: Session = Depends(get_db)) -> SeriesRepositoryImpl:
    return SeriesRepositoryImpl(db)


def get_comment_repo(db: Session = Depends(get_db)) -> CommentRepositoryImpl:
    return CommentRepositoryImpl(db)


def get_like_repo(db: Session = Depends(get_db)) -> LikeRepositoryImpl:
    return LikeRepositoryImpl(db)


def get_follow_repo(db: Session = Depends(get_db)) -> FollowRepositoryImpl:
    return FollowRepositoryImpl(db)


def get_notification_repo(db: Session = Depends(get_db)) -> NotificationRepositoryImpl:
    return NotificationRepositoryImpl(db)


def get_report_repo(db: Session = Depends(get_db)) -> ReportRepositoryImpl:
    return ReportRepositoryImpl(db)


def get_block_repo(db: Session = Depends(get_db)) -> BlockRepositoryImpl:
    return BlockRepositoryImpl(db)


# ------------------------------------------------------------------- services


def get_crawler_service() -> CrawlerServiceImpl:
    return CrawlerServiceImpl()


# ---------------------------------------------------------------- rate limiting


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """로그인했으면 사용자 ID, 아니면 None.

    공개 페이지에서 "내가 좋아요를 눌렀는지" 같은 개인화 정보를 곁들일 때 쓴다.
    인증이 없어도 401 을 내지 않는다.
    """
    if not credentials or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("sub")
    return user_id if isinstance(user_id, str) else None


def enforce_rate_limit(action: str, identity: str) -> None:
    """제한을 넘으면 429. 라우터에서 직접 호출한다."""
    decision = rate_limiter.check(action, identity)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="요청이 너무 잦습니다. 잠시 후 다시 시도해주세요.",
            headers={"Retry-After": str(decision.retry_after)},
        )


def client_identity(request: Request, user_id: Optional[str] = None) -> str:
    """레이트리밋 키. 로그인 사용자는 ID, 익명은 IP 기준."""
    if user_id:
        return f"u:{user_id}"
    return f"ip:{_client_ip(request)}"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )


def viewer_key(request: Request, user_id: Optional[str] = None) -> str:
    """조회 중복 제거용 뷰어 식별자.

    IP 를 그대로 저장하지 않는다. 조회수를 세는 데 개인정보가 필요하지 않고,
    "같은 사람이 다시 왔나" 만 알면 되므로 해시로 충분하다.
    SECRET_KEY 를 키로 쓴 HMAC 이라 DB 만 새어도 원래 IP 를 되돌릴 수 없다.
    """
    if user_id:
        return hashlib.sha256(f"u:{user_id}".encode()).hexdigest()

    raw = f"{_client_ip(request)}|{request.headers.get('user-agent', '')}"
    return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()


def get_admin_user_id(
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepositoryImpl = Depends(get_user_repo),
) -> str:
    """운영자만 통과시킨다.

    권한 없음을 404 로 답한다. 403 을 내면 "그런 화면이 있긴 하다" 를 알려주게 되고,
    운영자 화면의 존재를 굳이 광고할 이유가 없다.
    """
    user = user_repo.get_by_id(user_id)
    if not user or user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="찾을 수 없습니다.")
    return user_id
