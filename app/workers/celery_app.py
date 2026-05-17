"""
Celery Application — Real Task Queue with Redis Broker
=======================================================
Handles background tasks: AI generation, notifications, reminders, etc.
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "midnight_scholar",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # Serialization
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[settings.CELERY_ACCEPT_CONTENT],
    result_serializer=settings.CELERY_TASK_SERIALIZER,

    # Timezone & UTC
    timezone="UTC",
    enable_utc=True,

    # Task tracking & limits
    task_track_started=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,

    # Worker settings
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=1000,

    # Result backend
    result_expires=settings.CELERY_RESULT_EXPIRES,

    # Periodic tasks (Beat)
    beat_scheduler="celery.beat:PersistentScheduler",
)

# Auto-discover tasks from all workers modules
celery_app.autodiscover_tasks(["app.workers"])
