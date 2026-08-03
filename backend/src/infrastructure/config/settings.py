from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://devshiplog:devshiplog@localhost:3306/devshiplog"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM APIs
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # LLM 모델 및 단가 (USD / 1M tokens)
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_INPUT_COST_PER_1M: float = 0.15
    LLM_OUTPUT_COST_PER_1M: float = 0.60

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "ap-northeast-2"

    # Security
    SECRET_KEY: str = INSECURE_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # CORS (환경변수로는 JSON 배열로 전달: CORS_ORIGINS=["http://localhost:3000"])
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # 크롤러
    CRAWLER_TIMEOUT_SECONDS: float = 15.0
    CRAWLER_MAX_BYTES: int = 5 * 1024 * 1024  # 5MB
    # 사설/루프백 대역 크롤링 허용 여부. 프로덕션에서는 반드시 False (SSRF 방어)
    CRAWLER_ALLOW_PRIVATE_NETWORK: bool = False

    # 사용량 제한 (월간 LLM Job 수). 0 이면 무제한
    MONTHLY_JOB_QUOTA: int = 100

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """프로덕션에서 기본 시크릿/디버그 설정으로 기동되는 것을 막는다."""
        if not self.is_production:
            return self

        problems = []
        if self.SECRET_KEY == INSECURE_SECRET_KEY or len(self.SECRET_KEY) < 32:
            problems.append("SECRET_KEY (32자 이상의 임의 문자열이어야 합니다)")
        if not self.OPENAI_API_KEY:
            problems.append("OPENAI_API_KEY (비어 있습니다)")
        if self.DEBUG:
            problems.append("DEBUG (프로덕션에서는 False 여야 합니다)")
        if self.CRAWLER_ALLOW_PRIVATE_NETWORK:
            problems.append("CRAWLER_ALLOW_PRIVATE_NETWORK (프로덕션에서는 False 여야 합니다)")

        if problems:
            raise ValueError(
                "ENVIRONMENT=production 이지만 다음 설정이 안전하지 않습니다: " + ", ".join(problems)
            )
        return self


settings = Settings()
