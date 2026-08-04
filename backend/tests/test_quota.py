"""LLM 호출은 실제 비용이 나가므로 쿼터가 반드시 걸려야 한다."""

import uuid

import pytest

from src.application.errors import QuotaExceededError
from src.application.services.quota import assert_within_quota, month_start
from src.domain.enums import JobType, SourceType
from src.infrastructure.config.settings import settings
from src.infrastructure.database.models.source import Source
from src.infrastructure.database.repositories.job_repository_impl import JobRepositoryImpl


def test_month_start_is_first_day_at_midnight():
    start = month_start()
    assert start.day == 1
    assert (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)


def test_quota_allows_when_under_limit(db_session, monkeypatch):
    monkeypatch.setattr(settings, "MONTHLY_JOB_QUOTA", 3)
    repo = JobRepositoryImpl(db_session)
    assert_within_quota(repo, "user-1")  # 예외 없음


def test_quota_blocks_when_limit_reached(db_session, monkeypatch, client, auth_headers):
    monkeypatch.setattr(settings, "MONTHLY_JOB_QUOTA", 2)
    user_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]

    repo = JobRepositoryImpl(db_session)
    repo.create(user_id=user_id, job_type=JobType.DRAFT)
    repo.create(user_id=user_id, job_type=JobType.DRAFT)

    with pytest.raises(QuotaExceededError):
        assert_within_quota(repo, user_id)


def test_zero_quota_means_unlimited(db_session, monkeypatch, client, auth_headers):
    monkeypatch.setattr(settings, "MONTHLY_JOB_QUOTA", 0)
    user_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]

    repo = JobRepositoryImpl(db_session)
    for _ in range(5):
        repo.create(user_id=user_id, job_type=JobType.DRAFT)

    assert_within_quota(repo, user_id)  # 예외 없음


def test_create_draft_returns_429_when_quota_exhausted(
    db_session, monkeypatch, client, auth_headers
):
    monkeypatch.setattr(settings, "MONTHLY_JOB_QUOTA", 1)
    user_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]

    JobRepositoryImpl(db_session).create(user_id=user_id, job_type=JobType.DRAFT)

    source = Source(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=SourceType.RAW,
        origin="raw_text",
        title="소스",
        content="본문",
        extracted_json={},
    )
    db_session.add(source)
    db_session.commit()

    response = client.post(
        "/api/v1/drafts",
        headers=auth_headers,
        json={
            "source_ids": [source.id],
            "type": "implementation",
            "audience": "intermediate",
            "length": "default",
            "use_style_profile": False,
        },
    )
    assert response.status_code == 429
