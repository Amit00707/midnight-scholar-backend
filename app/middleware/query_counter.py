"""
Query Counter Middleware — Log N+1 Query Detection
===================================================
Counts and logs queries per request, warning on potential N+1 issues.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Store query count per request context
_query_counts = {}


def attach_query_counter(engine: Engine):
    """Register query counter listeners on the SQLAlchemy engine."""

    @event.listens_for(engine, "before_cursor_execute", propagate=True)
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Increment query count before execution."""
        if not hasattr(conn.info, 'query_count'):
            conn.info.query_count = 0
        conn.info.query_count += 1

    @event.listens_for(engine, "after_cursor_execute", propagate=True)
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Track executed queries (optional: for detailed monitoring)."""
        pass


class QueryCounterMiddleware(BaseHTTPMiddleware):
    """Middleware to count queries per request and warn on N+1 patterns."""

    async def dispatch(self, request: Request, call_next):
        """Track query count for this request."""
        # Store starting request context
        request.state.query_count_start = 0

        try:
            response = await call_next(request)

            # Log if query count exceeds threshold
            query_count = getattr(request.state, 'query_count', 0)

            if query_count > 3:
                logger.warning(
                    f"⚠️ Potential N+1 Query: {request.method} {request.url.path} "
                    f"executed {query_count} queries (threshold: 3)"
                )
            elif query_count > 0:
                logger.debug(
                    f"✓ {request.method} {request.url.path} - {query_count} queries"
                )

            # Add query count header for debugging
            response.headers["X-Query-Count"] = str(query_count)

            return response
        except Exception as e:
            logger.error(f"Error in query counter middleware: {e}")
            raise
