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
