"""
Database Session — Async PostgreSQL Engine
============================================
Creates the async SQLAlchemy engine and provides session dependency.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def _build_engine():
    """Build engine lazily — validates DATABASE_URL at startup."""
    db_url = settings.DATABASE_URL

    # Fix common mistakes: replace placeholder or wrong prefix
    if not db_url or "get from" in db_url or db_url.startswith("postgresql://"):
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            raise RuntimeError(
                "DATABASE_URL is not configured correctly. "
                "Please set it in Render Environment Variables. "
                f"Current value: {db_url[:30]}..."
            )

    return create_async_engine(db_url, echo=False, pool_size=5, max_overflow=5)


engine = _build_engine()
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
