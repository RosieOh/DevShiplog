"""모든 ORM 모델을 한 곳에서 import 한다.

Alembic 의 autogenerate 와 SQLAlchemy 의 관계 해석(문자열로 참조하는 back_populates)이
동작하려면 매퍼가 전부 등록되어 있어야 한다.
"""

# --- 글쓰기 도구 -----------------------------------------------------------
from src.infrastructure.database.models.user import User
from src.infrastructure.database.models.style_profile import StyleProfile
from src.infrastructure.database.models.source import Source
from src.infrastructure.database.models.draft import Draft
from src.infrastructure.database.models.draft_version import DraftVersion
from src.infrastructure.database.models.risk_finding import RiskFinding
from src.infrastructure.database.models.job import Job
from src.infrastructure.database.models.usage_log import UsageLog
from src.infrastructure.database.models.template import Template
from src.infrastructure.database.models.schedule import Schedule

# --- 블로그 플랫폼 ---------------------------------------------------------
from src.infrastructure.database.models.post import Post
from src.infrastructure.database.models.tag import PostTag, Tag
from src.infrastructure.database.models.series import Series, SeriesPost
from src.infrastructure.database.models.social import Comment, Follow, Notification, PostLike
from src.infrastructure.database.models.moderation import Report, UserBlock
from src.infrastructure.database.models.post_view import PostView
from src.infrastructure.database.models.password_reset import PasswordResetToken
from src.infrastructure.database.models.tech import PostSignal, PostStack

__all__ = [
    "User",
    "StyleProfile",
    "Source",
    "Draft",
    "DraftVersion",
    "RiskFinding",
    "Job",
    "UsageLog",
    "Template",
    "Schedule",
    "Post",
    "Tag",
    "PostTag",
    "Series",
    "SeriesPost",
    "Comment",
    "PostLike",
    "Follow",
    "Notification",
    "Report",
    "UserBlock",
    "PostView",
    "PasswordResetToken",
    "PostStack",
    "PostSignal",
]
