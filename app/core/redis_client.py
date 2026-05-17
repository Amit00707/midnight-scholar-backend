"""
Redis Client Helper — Caching & Session Management
===================================================
Provides simple interface for Redis operations.
"""

import json
import logging
from typing import Any, Optional
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client connection."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=10,
            )
            _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    return _redis_client


def cache_get(key: str) -> Optional[dict]:
    """Retrieve JSON value from cache."""
    try:
        client = get_redis_client()
        value = client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Store JSON value in cache with TTL (seconds)."""
    try:
        client = get_redis_client()
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Delete value from cache."""
    try:
        client = get_redis_client()
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        return False


def cache_incr(key: str, ttl: int = 3600) -> int:
    """Increment counter (used for rate limiting)."""
    try:
        client = get_redis_client()
        value = client.incr(key)
        if value == 1:  # First increment, set expiry
            client.expire(key, ttl)
        return value
    except Exception as e:
        logger.warning(f"Cache incr error for key {key}: {e}")
        return 0


def cache_exists(key: str) -> bool:
    """Check if key exists in cache."""
    try:
        client = get_redis_client()
        return bool(client.exists(key))
    except Exception as e:
        logger.warning(f"Cache exists error for key {key}: {e}")
        return False


def close_redis_client():
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
            _redis_client = None
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")
