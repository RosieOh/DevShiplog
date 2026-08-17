from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://devshiplog:devshiplog@localhost:3306/devshiplog"
    # 커넥션 풀.
    #
    # SQLAlchemy 기본값은 5+10=15 인데, 동기 엔드포인트를 돌리는 스레드풀은 40 이다.
    # 40 개 스레드가 15 개 커넥션을 두고 다투면 나머지는 줄을 서고, 줄이 길어지면
    # 스레드가 전부 대기에 묶여 /health 조차 답하지 못한다 (실측으로 확인).
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 20
    # 기본 30초는 너무 길다. 30초를 기다린 응답은 이미 사용자가 떠난 뒤고,
    # 그동안 스레드만 붙잡고 있어서 장애를 키운다. 빨리 실패하는 편이 낫다.
    DB_POOL_TIMEOUT: int = 5

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

    # 업로드 (커버 이미지·아바타)
    UPLOAD_DIR: str = "uploads"
    UPLOAD_PUBLIC_PREFIX: str = "/uploads"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5MB

    # 저장소 백엔드: "s3" | "local".
    #
    # 기본은 s3 이고, 개발에서는 docker compose 의 MinIO 를 가리킨다 (MinIO 는 S3 와
    # API 가 같다). local 은 오브젝트 저장소 없이 잠깐 돌려볼 때만 쓴다 — 서버가
    # 2대 이상이면 파일을 서로 못 보고, 컨테이너를 재배포하면 사라진다.
    STORAGE_BACKEND: str = "s3"
    STORAGE_S3_BUCKET: str = "devshiplog"
    STORAGE_S3_REGION: str = "us-east-1"
    STORAGE_S3_ACCESS_KEY: str = "devshiplog"
    STORAGE_S3_SECRET_KEY: str = "devshiplog1234"
    # MinIO·R2 등 S3 호환 저장소 주소. AWS S3 를 쓰면 비운다.
    STORAGE_S3_ENDPOINT: str = "http://localhost:9000"
    # 브라우저가 이미지를 받아갈 주소.
    # 컨테이너 안에서는 minio:9000 으로 붙지만 브라우저는 그 호스트명을 모른다.
    STORAGE_PUBLIC_BASE_URL: str = "http://localhost:9000/devshiplog"

    # 메일 (비밀번호 재설정·알림). SMTP_HOST 가 비면 발송하지 않고 로그만 남긴다.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    MAIL_FROM: str = "no-reply@devshiplog.com"
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # 공개 페이지 캐시 무효화 통지 대상 (Next 서버).
    # 비워두면 통지하지 않고 시간 기반 재검증에만 의존한다.
    FRONTEND_ORIGIN: str = ""
    REVALIDATE_SECRET: str = ""

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    # 로그와 오류 화면에 같이 실린다. "어느 버전에서 난 오류인가" 를 알 수 없으면
    # 배포 직후 생긴 오류인지 원래 있던 것인지 구분할 방법이 없다.
    APP_VERSION: str = "0.1.0"

    # Observability
    # 배포에서는 JSON 이 기본이어야 검색이 된다. 개발에서는 사람이 읽는 형식.
    LOG_JSON: bool = False
    # 비어 있으면 프로세스 내 수집기만 쓴다. 외부 서비스 가입을 전제로 하면
    # 결국 아무것도 안 붙이고 넘어가게 된다.
    SENTRY_DSN: str = ""

    # 알림. 오류가 화면에 쌓여도 아무도 안 보면 모르는 것과 같다.
    # 둘 다 비어 있으면 로그만 남긴다.
    ALERT_EMAIL: str = ""
    ALERT_WEBHOOK_URL: str = ""  # Slack/Discord Incoming Webhook
    # 같은 오류로 알림이 쏟아지면 사람은 알림을 끈다. 끈 알림은 없느니만 못하다.
    ALERT_ERROR_WINDOW_MINUTES: int = 60
    ALERT_REPORT_WINDOW_MINUTES: int = 30

    # 하트비트(데드맨 스위치).
    # 위의 알림은 전부 앱이 살아 있어야 나간다. 프로세스가 죽으면 아무 연락도 안 온다.
    # 주기적으로 여기에 신호를 보내고, 끊기면 바깥에서 알리게 한다.
    # 예: https://hc-ping.com/<uuid> (Healthchecks.io)
    HEARTBEAT_URL: str = ""
    HEARTBEAT_INTERVAL_SECONDS: int = 300

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
        if self.STORAGE_BACKEND != "s3":
            # 로컬 디스크는 인스턴스가 늘어나는 순간 파일이 갈라지고, 재배포하면 사라진다.
            problems.append("STORAGE_BACKEND (프로덕션에서는 s3 여야 합니다)")
        elif not self.STORAGE_S3_BUCKET:
            problems.append("STORAGE_S3_BUCKET (비어 있습니다)")
        elif self.STORAGE_S3_SECRET_KEY == "devshiplog1234":
            # 개발용 MinIO 기본 자격증명 그대로 뜨는 것을 막는다.
            problems.append("STORAGE_S3_SECRET_KEY (개발용 기본값입니다)")
        elif "localhost" in self.STORAGE_PUBLIC_BASE_URL:
            # 이 주소가 글 본문에 그대로 박힌다. 잘못 뜨면 발행된 글의 이미지가
            # 전부 독자의 localhost 를 가리키게 되고, 나중에 고쳐도 DB 에 남는다.
            problems.append("STORAGE_PUBLIC_BASE_URL (localhost 를 가리키고 있습니다)")

        if problems:
            raise ValueError(
                "ENVIRONMENT=production 이지만 다음 설정이 안전하지 않습니다: " + ", ".join(problems)
            )
        return self


settings = Settings()
