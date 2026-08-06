"""도메인 어휘(enum) 정의.

이 모듈은 어떤 상위 계층에도 의존하지 않는다.
application / ports 계층은 상태값이 필요할 때 infrastructure 의 ORM 모델이 아니라
이 모듈을 import 한다. (헥사고날 의존성 방향 유지)
"""

import enum


class DraftStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class SourceType(str, enum.Enum):
    URL = "url"
    RAW = "raw"


class StyleProfileStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobType(str, enum.Enum):
    EXTRACT = "extract"
    STYLE = "style"
    DRAFT = "draft"
    TRANSFORM = "transform"
    SAFETY = "safety"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RiskCategory(str, enum.Enum):
    TOKEN = "token"
    EMAIL = "email"
    PHONE = "phone"
    INTERNAL_URL = "internal_url"
    COMPANY = "company"
    SECRET = "secret"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MASKED = "masked"
    DELETED = "deleted"
    IGNORED = "ignored"


class TransformType(str, enum.Enum):
    SHORTEN = "shorten"
    EXPAND = "expand"
    SIMPLIFY = "simplify"
    DEEPEN = "deepen"
    STYLE_STRONGER = "style_stronger"


class SafetyAction(str, enum.Enum):
    MASK = "mask"
    DELETE = "delete"
    IGNORE = "ignore"


class PostStatus(str, enum.Enum):
    """공개 발행물의 상태.

    Draft(비공개 작업본)와 Post(공개 스냅샷)는 별개다.
    자동저장이 공개된 글을 실시간으로 바꾸면 안 되기 때문이다.
    """

    PUBLISHED = "published"
    # 작성자가 다시 내림 (URL 은 남기고 404 처리)
    UNLISTED = "unlisted"
    # 운영자가 가림 (신고 처리 결과)
    HIDDEN = "hidden"


class NotificationType(str, enum.Enum):
    COMMENT = "comment"
    REPLY = "reply"
    LIKE = "like"
    FOLLOW = "follow"


class ReportTargetType(str, enum.Enum):
    POST = "post"
    COMMENT = "comment"
    USER = "user"


class ReportReason(str, enum.Enum):
    SPAM = "spam"
    ABUSE = "abuse"
    SENSITIVE = "sensitive"
    COPYRIGHT = "copyright"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class SignalKind(str, enum.Enum):
    """독자가 보내는 "지금도 되나요?" 신호.

    좋아요와 다르다. 좋아요는 "좋았다" 고, 이건 "따라 해봤다" 다.
    따라 해본 사람만 보낼 수 있는 신호라 수가 적지만 훨씬 무겁다.
    """

    WORKS = "works"      # 따라 해봤고 됐다
    BROKEN = "broken"    # 따라 해봤는데 안 된다
