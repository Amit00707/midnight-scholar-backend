"""
Pytest Fixtures — Async Test Configuration
============================================
Provides async fixtures for FastAPI app, test database, and user fixtures.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.core.security import hash_password, create_access_token
from app.database.models.user import User, UserRole
from app.database.models.notification import NotificationPreference
from app.database.session import Base
from main import app as cors_app
from fastapi import FastAPI

# Get the actual FastAPI app (under CORS middleware)
if hasattr(cors_app, 'app') and isinstance(cors_app.app, FastAPI):
    app = cors_app.app
else:
    app = cors_app


# Override settings for testing
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create an in-memory SQLite test database with async connection.
    Creates all tables and cleans up after each test.
    """
    # Use in-memory SQLite for fast tests
    DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        DATABASE_URL_TEST,
        echo=False,
        connect_args={"timeout": 30}
    )

    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with async_session_factory() as session:
        yield session
        await session.close()

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest.fixture
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an AsyncClient for testing FastAPI endpoints.
    Overrides the database dependency to use test_db.
    """

    async def get_test_db():
        yield test_db

    # Override the database dependency
    from app.database.session import get_db
    app.dependency_overrides[get_db] = get_test_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test student user in the database."""
    user = User(
        email="student@example.com",
        name="Test Student",
        hashed_password=hash_password("password123"),
        role=UserRole.student,
        is_verified=True,
        avatar_url="https://example.com/avatar.jpg",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_admin(test_db: AsyncSession) -> User:
    """Create a test admin user in the database."""
    user = User(
        email="admin@example.com",
        name="Test Admin",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.admin,
        is_verified=True,
        avatar_url="https://example.com/admin-avatar.jpg",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_teacher(test_db: AsyncSession) -> User:
    """Create a test teacher user in the database."""
    user = User(
        email="teacher@example.com",
        name="Test Teacher",
        hashed_password=hash_password("teacherpass123"),
        role=UserRole.teacher,
        is_verified=True,
        avatar_url="https://example.com/teacher-avatar.jpg",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_jwt_token(test_user: User) -> str:
    """Generate a valid JWT token for test_user."""
    token_data = {"sub": str(test_user.id), "email": test_user.email}
    token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=30)
    )
    return token


@pytest.fixture
async def test_admin_jwt_token(test_admin: User) -> str:
    """Generate a valid JWT token for test_admin."""
    token_data = {"sub": str(test_admin.id), "email": test_admin.email}
    token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=30)
    )
    return token


@pytest.fixture
async def test_teacher_jwt_token(test_teacher: User) -> str:
    """Generate a valid JWT token for test_teacher."""
    token_data = {"sub": str(test_teacher.id), "email": test_teacher.email}
    token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=30)
    )
    return token


@pytest.fixture
async def notification_preference_for_test_user(test_db: AsyncSession, test_user: User) -> NotificationPreference:
    """Create default notification preferences for test_user."""
    pref = NotificationPreference(
        user_id=test_user.id,
        email_enabled=True,
        push_enabled=True,
        in_app_enabled=True,
        streak_reminders=True,
        quiz_alerts=True,
        achievements=True,
        messages=True,
        reading_reminders=True,
        announcements=True,
        class_assignments=True,
        comment_replies=True,
        quiet_hours_enabled=False,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        digest_frequency="daily"
    )
    test_db.add(pref)
    await test_db.commit()
    await test_db.refresh(pref)
    return pref
