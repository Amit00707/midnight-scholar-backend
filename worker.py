#!/usr/bin/env python
"""
Celery Worker Starter
======================
Run this to start the Celery worker:
    python worker.py
or:
    celery -A worker worker --loglevel=info
"""

import os
import logging
from app.workers.celery_app import celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Celery worker...")
    celery_app.start(
        argv=[
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--prefetch-multiplier=4",
        ]
    )
