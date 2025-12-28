from celery import Celery
from infrastructure.config.settings import settings

celery_app = Celery(
    "devshiplog",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
)

# Task 모듈 자동 발견
celery_app.autodiscover_tasks(["infrastructure.queue.tasks"])

