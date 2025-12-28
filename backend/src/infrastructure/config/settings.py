from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://devshiplog:devshiplog@localhost:3306/devshiplog"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM APIs
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    AWS_REGION: str = "ap-northeast-2"
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

