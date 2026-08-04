from celery import Celery

from src.infrastructure.config.settings import settings

celery_app = Celery(
    "devshiplog",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    # autodiscover 는 "<package>.tasks" 규칙을 따르므로, 우리 레이아웃에서는
    # 모듈을 명시적으로 등록하는 편이 확실하다.
    include=[
        "src.infrastructure.queue.tasks.draft_generation_tasks",
        "src.infrastructure.queue.tasks.transform_tasks",
        "src.infrastructure.queue.tasks.style_profile_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes (긴 글 생성 여유)
    task_soft_time_limit=540,  # 9 minutes
    # 워커가 죽어도 작업을 잃지 않도록 ack 를 작업 완료 후로 미룬다.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
