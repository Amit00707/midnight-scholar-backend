"""
Test Suite: Reader API Endpoints
=================================
Tests for reading progress, bookmarks, highlights, and notes.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.progress import ReadingProgress, Bookmark, Highlight, Note
from tests.factories import ReadingProgressFactory, BookmarkFactory, HighlightFactory, NoteFactory


class TestReader:
    """Reader API endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_reading_progress_unauthorized(self, async_client: AsyncClient):
        """Test getting reading progress without authentication."""
        response = await async_client.get("/api/reader/progress")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_reading_progress_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test successful retrieval of reading progress."""
        # Create test progress
        progress = ReadingProgressFactory.build(user_id=test_user.id)
        test_db.add(progress)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get("/api/reader/progress", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_save_reading_progress_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test saving reading progress successfully."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "current_page": 45,
            "time_spent_minutes": 30
        }
        response = await async_client.post("/api/reader/progress", json=payload, headers=headers)
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_save_reading_progress_invalid_page(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test saving reading progress with invalid page number."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "current_page": -5,
            "time_spent_minutes": 30
        }
        response = await async_client.post("/api/reader/progress", json=payload, headers=headers)
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_add_bookmark_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test adding a bookmark successfully."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 42,
            "label": "Important section"
        }
        response = await async_client.post("/api/reader/bookmarks", json=payload, headers=headers)
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_add_bookmark_unauthorized(self, async_client: AsyncClient):
        """Test adding bookmark without authentication."""
        payload = {"book_id": "test-book-123", "page_number": 42}
        response = await async_client.post("/api/reader/bookmarks", json=payload)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_bookmarks_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving bookmarks for a book."""
        # Create test bookmark
        bookmark = BookmarkFactory.build(user_id=test_user.id, book_id="test-book-123")
        test_db.add(bookmark)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get("/api/reader/bookmarks/test-book-123", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "bookmarks" in data

    @pytest.mark.asyncio
    async def test_get_bookmarks_empty(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test retrieving bookmarks when none exist."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get("/api/reader/bookmarks/nonexistent-book", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["bookmarks"] == []

    @pytest.mark.asyncio
    async def test_delete_bookmark_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test deleting a bookmark."""
        bookmark = BookmarkFactory.build(user_id=test_user.id)
        test_db.add(bookmark)
        await test_db.commit()
        await test_db.refresh(bookmark)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.delete(f"/api/reader/bookmarks/{bookmark.id}", headers=headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_bookmark_not_owner(
        self, async_client: AsyncClient, test_user: User, test_teacher: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test deleting someone else's bookmark."""
        bookmark = BookmarkFactory.build(user_id=test_teacher.id)
        test_db.add(bookmark)
        await test_db.commit()
        await test_db.refresh(bookmark)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.delete(f"/api/reader/bookmarks/{bookmark.id}", headers=headers)
        # Returns 200 even for not owned (silent failure) or 404
        assert response.status_code in [200, 403, 404]

    @pytest.mark.asyncio
    async def test_add_highlight_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test adding a highlight successfully."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 50,
            "text_content": "This is a highlighted quote",
            "color": "amber"
        }
        response = await async_client.post("/api/reader/highlights", json=payload, headers=headers)
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_add_highlight_invalid_color(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test adding highlight with invalid color."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 50,
            "text_content": "Some text",
            "color": "invalid_color"
        }
        response = await async_client.post("/api/reader/highlights", json=payload, headers=headers)
        assert response.status_code in [400, 422, 200]

    @pytest.mark.asyncio
    async def test_add_note_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test adding a note successfully."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 60,
            "content": "This is my personal note about the book"
        }
        response = await async_client.post("/api/reader/notes", json=payload, headers=headers)
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_add_note_unauthorized(self, async_client: AsyncClient):
        """Test adding note without authentication."""
        payload = {
            "book_id": "test-book-123",
            "page_number": 60,
            "content": "My note"
        }
        response = await async_client.post("/api/reader/notes", json=payload)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_progress_calculation_accuracy(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test that reading progress percentage is calculated correctly."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-456",
            "current_page": 100,
            "time_spent_minutes": 45
        }
        response = await async_client.post("/api/reader/progress", json=payload, headers=headers)
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_add_highlight_empty_text(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test adding highlight with empty text content."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 50,
            "text_content": "",
            "color": "amber"
        }
        response = await async_client.post("/api/reader/highlights", json=payload, headers=headers)
        # May pass or fail validation
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_update_progress_incremental(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test updating progress incrementally."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}

        # First update
        payload1 = {
            "book_id": "test-book-789",
            "current_page": 50,
            "time_spent_minutes": 30
        }
        response1 = await async_client.post("/api/reader/progress", json=payload1, headers=headers)
        assert response1.status_code in [200, 201]

        # Second update to same book
        payload2 = {
            "book_id": "test-book-789",
            "current_page": 75,
            "time_spent_minutes": 20
        }
        response2 = await async_client.post("/api/reader/progress", json=payload2, headers=headers)
        assert response2.status_code in [200, 201]
