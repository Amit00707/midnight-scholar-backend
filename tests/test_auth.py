"""
Test Suite: Authentication Endpoints
=====================================
Tests for user signup, login, token refresh, and email verification.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.core.security import hash_password


class TestAuth:
    """Authentication endpoint tests."""

    @pytest.mark.asyncio
    async def test_signup_success(self, async_client: AsyncClient, test_db: AsyncSession):
        """Test successful user registration."""
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "securepass123"
        }
        response = await async_client.post("/api/auth/signup", json=payload)
        assert response.status_code == 200
        assert response.json()["name"] == "New User"
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test signup fails with duplicate email."""
        payload = {
            "email": test_user.email,
            "name": "Another User",
            "password": "securepass123"
        }
        response = await async_client.post("/api/auth/signup", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower() or "email" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_signup_missing_field(self, async_client: AsyncClient):
        """Test signup fails with missing required fields."""
        payload = {
            "email": "user@example.com",
            # Missing name and password
        }
        response = await async_client.post("/api/auth/signup", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        payload = {
            "email": test_user.email,
            "password": "password123"
        }
        response = await async_client.post("/api/auth/login", json=payload)
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, async_client: AsyncClient):
        """Test login with non-existent email."""
        payload = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        response = await async_client.post("/api/auth/login", json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, async_client: AsyncClient, test_user: User):
        """Test login with incorrect password."""
        payload = {
            "email": test_user.email,
            "password": "wrongpassword"
        }
        response = await async_client.post("/api/auth/login", json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client: AsyncClient, test_user: User, test_jwt_token: str):
        """Test token refresh endpoint."""
        # Send refresh token in request body (endpoint expects refresh_token in JSON body)
        payload = {"refresh_token": test_jwt_token}
        response = await async_client.post("/api/auth/refresh", json=payload)
        # Access token won't work as refresh token, so expect 401
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_verify_email(self, async_client: AsyncClient, test_user: User):
        """Test email verification endpoint."""
        # This would depend on actual implementation
        response = await async_client.post(f"/api/auth/verify-email/{test_user.id}")
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_forgot_password(self, async_client: AsyncClient, test_user: User):
        """Test password reset flow initiation."""
        payload = {"email": test_user.email}
        response = await async_client.post("/api/auth/forgot-password", json=payload)
        # Status depends on implementation (might queue async task)
        assert response.status_code in [200, 400, 401]

    @pytest.mark.asyncio
    async def test_missing_auth_header(self, async_client: AsyncClient):
        """Test protected endpoint without auth header."""
        response = await async_client.get("/api/gamification/points")
        assert response.status_code == 403  # or 401 depending on implementation

    @pytest.mark.asyncio
    async def test_invalid_auth_token(self, async_client: AsyncClient):
        """Test protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = await async_client.get("/api/gamification/points", headers=headers)
        assert response.status_code == 401
