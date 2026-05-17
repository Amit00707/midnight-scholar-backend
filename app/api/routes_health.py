"""
Health Check Routes — System Status Monitoring
===============================================
Provides endpoints to check Redis, Celery, and overall system health.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.core.redis_client import get_redis_client
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """Overall system health status."""
    try:
        # Check Redis
        redis_ok = False
        try:
            client = get_redis_client()
            client.ping()
            redis_ok = True
        except Exception as e:
            logger.warning(f"Redis check failed: {e}")

        # Check Celery
        celery_ok = False
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            celery_ok = stats is not None and len(stats) > 0
        except Exception as e:
            logger.warning(f"Celery check failed: {e}")

        return {
            "status": "ok" if redis_ok and celery_ok else "degraded",
            "components": {
                "redis": "ok" if redis_ok else "down",
                "celery": "ok" if celery_ok else "no-workers",
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")


@router.get("/health/redis")
async def health_redis():
    """Check Redis connectivity."""
    try:
        client = get_redis_client()
        client.ping()
        return {"status": "ok", "service": "redis"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Redis Down: {str(e)}")


@router.get("/health/celery")
async def health_celery():
    """Check Celery worker status."""
    try:
        inspect = celery_app.control.inspect()

        # Get worker stats
        stats = inspect.stats()
        if stats is None:
            raise Exception("No workers available")

        active_workers = len(stats)
        active_tasks = sum(len(tasks) for tasks in (inspect.active() or {}).values())

        return {
            "status": "ok",
            "service": "celery",
            "workers": active_workers,
            "active_tasks": active_tasks,
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Celery Down: {str(e)}")


@router.post("/health/celery/ping")
async def celery_ping():
    """Ping all Celery workers."""
    try:
        inspect = celery_app.control.inspect()
        pings = inspect.ping()
        if pings is None:
            raise Exception("No workers to ping")
        return {"status": "ok", "workers_responded": len(pings)}
    except Exception as e:
        logger.error(f"Celery ping failed: {e}")
        raise HTTPException(status_code=503, detail=f"Celery Ping Failed: {str(e)}")
