"""
Database Session — Async PostgreSQL Engine (Lazy Init)
=======================================================
Engine is created lazily on first use — app starts even if DATABASE_URL
is not yet configured correctly.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# Lazy globals — set on first use
_engine = None
_session_factory = None


def _get_engine():
    global _engine, _session_factory

    if _engine is not None:
        return _engine

    from app.core.config import settings
    db_url = settings.DATABASE_URL

    # Auto-fix: postgresql:// → postgresql+asyncpg://
    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Validate URL
    if not db_url or "get from" in db_url or len(db_url) < 20:
        logger.error(f"DATABASE_URL is not set correctly: '{db_url[:40]}'")
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Please set it in Render → Environment Variables."
        )

    _engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=5)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


async def get_db():
    """FastAPI dependency that yields an async database session."""
    _get_engine()  # ensure engine is initialized
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Compatibility alias
def get_session_factory():
    _get_engine()
    return _session_factory
