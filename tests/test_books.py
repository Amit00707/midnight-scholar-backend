"""
Test Suite: Books API Endpoints
================================
Tests for book search, trending, recommendations, and user library management.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User


class TestBooks:
    """Books API endpoint tests."""

    @pytest.mark.asyncio
    async def test_search_books_success(self, async_client: AsyncClient):
        """Test successful book search."""
        response = await async_client.get("/api/books/search?q=python&limit=10&page=1")
        assert response.status_code == 200
        assert "results" in response.json() or "books" in response.json()

    @pytest.mark.asyncio
    async def test_search_books_empty_query(self, async_client: AsyncClient):
        """Test book search with empty query."""
        response = await async_client.get("/api/books/search?q=&limit=10&page=1")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_books_pagination(self, async_client: AsyncClient):
        """Test book search with pagination parameters."""
        response = await async_client.get("/api/books/search?q=the&limit=5&page=2")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_books_with_lang_filter(self, async_client: AsyncClient):
        """Test book search with language filter."""
        response = await async_client.get("/api/books/search?q=novel&lang=eng&limit=10")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_books_by_category(self, async_client: AsyncClient):
        """Test fetching books by category."""
        response = await async_client.get("/api/books/category/science?limit=12")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_books_by_category_with_sort(self, async_client: AsyncClient):
        """Test fetching books by category with sort parameter."""
        response = await async_client.get("/api/books/category/fiction?limit=10&sort=rating")
        assert response.status_code in [200, 502]

    @pytest.mark.asyncio
    async def test_trending_books(self, async_client: AsyncClient):
        """Test fetching trending books."""
        response = await async_client.get("/api/books/trending?limit=12")
        assert response.status_code in [200, 502]

    @pytest.mark.asyncio
    async def test_books_by_author(self, async_client: AsyncClient):
        """Test fetching books by author."""
        response = await async_client.get("/api/books/by-author?name=Stephen+King&limit=12")
        assert response.status_code in [200, 502]

    @pytest.mark.asyncio
    async def test_books_by_author_not_found(self, async_client: AsyncClient):
        """Test fetching books by non-existent author."""
        response = await async_client.get("/api/books/by-author?name=XyzNonExistentAuthorXyz&limit=12")
        assert response.status_code in [200, 502]

    @pytest.mark.asyncio
    async def test_personalized_recommendations_unauthorized(self, async_client: AsyncClient):
        """Test recommendations endpoint without authentication."""
        payload = {"interests": ["science", "technology"]}
        response = await async_client.post("/api/books/recommendations", json=payload)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_personalized_recommendations_authenticated(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test personalized recommendations with valid token."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {"interests": ["science", "technology"], "limit_per_category": 3}
        response = await async_client.post(
            "/api/books/recommendations", json=payload, headers=headers
        )
        assert response.status_code in [200, 502]

    @pytest.mark.asyncio
    async def test_get_book_details_by_key(self, async_client: AsyncClient):
        """Test fetching book details by OpenLibrary key."""
        # This test assumes the endpoint exists and accepts a book key
        response = await async_client.get("/api/books/OL45883W")
        assert response.status_code in [200, 404, 502]

    @pytest.mark.asyncio
    async def test_search_books_max_limit(self, async_client: AsyncClient):
        """Test book search with max allowed limit."""
        response = await async_client.get("/api/books/search?q=book&limit=40&page=1")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_books_exceed_max_limit(self, async_client: AsyncClient):
        """Test book search exceeding max limit."""
        response = await async_client.get("/api/books/search?q=book&limit=100&page=1")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trending_books_default_limit(self, async_client: AsyncClient):
        """Test trending books with default limit."""
        response = await async_client.get("/api/books/trending")
        assert response.status_code in [200, 502]

    @pytest.mark.asyncio
    async def test_search_books_invalid_page(self, async_client: AsyncClient):
        """Test book search with invalid page number."""
        response = await async_client.get("/api/books/search?q=book&page=0")
        assert response.status_code == 422
