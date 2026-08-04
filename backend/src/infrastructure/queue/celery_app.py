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
    #
    # 브로커가 죽었을 때 빨리 실패한다.
    #
    # 기본값은 무한 재시도라, Redis 가 내려가면 `.delay()` 를 부른 API 요청이
    # 응답을 못 하고 매달린다. 큐에 넣지 못한 것은 사실이고, 사용자에게는
    # "지금은 안 된다" 를 바로 알려주는 편이 낫다 (재시도는 사용자가 정한다).
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
        "max_retries": 2,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
    # 발행(.delay) 자체의 재시도 정책. 위 옵션과 별개로 지정해야 한다.
    task_publish_retry_policy={
        "max_retries": 2,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
)
