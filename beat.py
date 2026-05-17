#!/usr/bin/env python
"""
Celery Beat Scheduler Starter
==============================
Runs periodic tasks on schedule.
Run this to start the scheduler:
    python beat.py
or:
    celery -A worker beat --loglevel=info
"""

import logging
from app.workers.celery_app import celery_app
from celery.beat import EmbeddedScheduleEntry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define periodic tasks
celery_app.conf.beat_schedule = {
    "check-streaks-hourly": {
        "task": "check_streaks_task",
        "schedule": 3600,  # Every hour
        "kwargs": {}
    },
    "send-daily-reminders": {
        "task": "send_daily_reminders_task",
        "schedule": 86400,  # Every 24 hours
        "kwargs": {},
        "options": {
            "expire_time": 3600,  # Task expires after 1 hour
        }
    },
}

if __name__ == "__main__":
    logger.info("Starting Celery Beat scheduler...")
    logger.info("Scheduled tasks:")
    for task_name, task_config in celery_app.conf.beat_schedule.items():
        logger.info(f"  - {task_name}: {task_config['task']} every {task_config['schedule']}s")

    celery_app.start(
        argv=[
            "beat",
            "--loglevel=info",
            "--scheduler=celery.beat:PersistentScheduler",
        ]
    )
