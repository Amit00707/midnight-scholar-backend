"""
Query Monitor — Slow Query Detection and Logging
=================================================
Logs queries that take longer than threshold (default 100ms).
"""

import time
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Threshold for logging slow queries (in seconds)
SLOW_QUERY_THRESHOLD = 0.1  # 100ms


def attach_slow_query_monitor(engine: Engine):
    """Register slow query monitoring listeners on the SQLAlchemy engine."""

    @event.listens_for(engine, "before_cursor_execute", propagate=True)
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        if not hasattr(conn.info, 'query_start_times'):
            conn.info.query_start_times = []
        conn.info.query_start_times.append(time.time())

    @event.listens_for(engine, "after_cursor_execute", propagate=True)
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log slow queries."""
        if hasattr(conn.info, 'query_start_times') and conn.info.query_start_times:
            start_time = conn.info.query_start_times.pop()
            total_time = time.time() - start_time

            # Log queries exceeding threshold
            if total_time > SLOW_QUERY_THRESHOLD:
                # Sanitize statement for logging
                stmt_preview = statement.replace('\n', ' ')[:200]

                logger.warning(
                    f"🐌 SLOW QUERY ({total_time*1000:.2f}ms): {stmt_preview}...\n"
                    f"   Parameters: {str(parameters)[:100]}"
                )
