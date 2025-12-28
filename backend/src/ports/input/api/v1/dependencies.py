from fastapi import Depends
from sqlalchemy.orm import Session
from infrastructure.database.session import get_db
from infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from infrastructure.database.repositories.style_profile_repository_impl import StyleProfileRepositoryImpl
from infrastructure.database.repositories.source_repository_impl import SourceRepositoryImpl
from infrastructure.database.repositories.draft_repository_impl import DraftRepositoryImpl
from infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl
from infrastructure.database.repositories.risk_finding_repository_impl import RiskFindingRepositoryImpl
from infrastructure.external.llm.openai_client import OpenAIService
from infrastructure.external.crawler.crawler_service_impl import CrawlerServiceImpl


def get_user_repo(db: Session = Depends(get_db)):
    return UserRepositoryImpl(db)


def get_style_profile_repo(db: Session = Depends(get_db)):
    return StyleProfileRepositoryImpl(db)


def get_source_repo(db: Session = Depends(get_db)):
    return SourceRepositoryImpl(db)


def get_draft_repo(db: Session = Depends(get_db)):
    return DraftRepositoryImpl(db)


def get_job_repo(db: Session = Depends(get_db)):
    return JobRepositoryImpl(db)


def get_risk_finding_repo(db: Session = Depends(get_db)):
    return RiskFindingRepositoryImpl(db)


def get_llm_service():
    return OpenAIService()


def get_crawler_service():
    return CrawlerServiceImpl()

