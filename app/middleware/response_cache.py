"""
Response Cache Middleware — HTTP-Level Response Caching
========================================================
Caches GET responses at the HTTP level for 5 minutes.
"""

import json
import logging
from hashlib import md5
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.redis_client import cache_get, cache_set

logger = logging.getLogger(__name__)

# Endpoints that should never be cached
CACHE_EXCLUDED_PATHS = {
    "/notifications",
    "/preferences",
    "/auth",
    "/health",
    "/metrics",
    "/feed",  # Social feed changes frequently
    "/leaderboard",  # Leaderboard changes frequently
}

# Default cache TTL for GET responses (in seconds)
RESPONSE_CACHE_TTL = 300  # 5 minutes


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Cache GET responses to reduce database load."""

    async def dispatch(self, request: Request, call_next):
        """Check cache, execute request, and cache response."""

        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        # Skip excluded endpoints
        path = request.url.path
        if any(path.startswith(excluded) for excluded in CACHE_EXCLUDED_PATHS):
            return await call_next(request)

        # Generate cache key from URL and query params
        cache_key = f"response:{md5(str(request.url).encode()).hexdigest()}"

        # Try to get from cache
        cached_response = cache_get(cache_key)
        if cached_response is not None:
            logger.debug(f"Cache HIT: {path}")
            response = JSONResponse(cached_response)
            response.headers["X-Cache"] = "HIT"
            return response

        # Get actual response
        response = await call_next(request)

        # Cache successful responses
        if response.status_code == 200:
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                # Try to parse and cache as JSON
                data = json.loads(body)
                cache_set(cache_key, data, ttl=RESPONSE_CACHE_TTL)
                logger.debug(f"Cache SET: {path} (TTL: {RESPONSE_CACHE_TTL}s)")

                # Return response with cache headers
                response.headers["X-Cache"] = "MISS"
                response.headers["Cache-Control"] = f"public, max-age={RESPONSE_CACHE_TTL}"

                # Re-create response with cached body since we consumed the iterator
                return JSONResponse(data, status_code=response.status_code, headers=dict(response.headers))

            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"Could not cache response for {path}: {e}")
                response.headers["X-Cache"] = "SKIP"

        return response
