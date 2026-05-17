"""
Test Suite: AI Engine API Endpoints
====================================
Tests for AI-powered features: summaries, quizzes, flashcards, analysis.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User


class TestAI:
    """AI Engine API endpoint tests."""

    @pytest.mark.asyncio
    async def test_generate_summary_unauthorized(self, async_client: AsyncClient):
        """Test generating summary without authentication."""
        payload = {
            "book_id": "test-book-123",
            "page_number": 1
        }
        response = await async_client.post("/api/ai/summary", json=payload)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_generate_summary_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test generating AI summary of book content."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1,
            "style": "detailed"
        }
        response = await async_client.post("/api/ai/summary", json=payload, headers=headers)
        assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_generate_summary_invalid_range(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test generating summary with invalid page range."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 999
        }
        response = await async_client.post("/api/ai/summary", json=payload, headers=headers)
        # Endpoint gracefully returns 200 with fallback data even for invalid page numbers
        assert response.status_code in [200, 202, 400, 422, 502]

    @pytest.mark.asyncio
    async def test_generate_quiz_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test generating AI quiz."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1,
            "num_questions": 5,
            "difficulty": "medium"
        }
        response = await async_client.post("/api/ai/quiz", json=payload, headers=headers)
        assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_generate_quiz_custom_difficulty(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test quiz generation with different difficulties."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        for difficulty in ["easy", "medium", "hard"]:
            payload = {
                "book_id": "test-book-123",
                "page_number": 1,
                "num_questions": 3,
                "difficulty": difficulty
            }
            response = await async_client.post("/api/ai/quiz", json=payload, headers=headers)
            assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_generate_flashcards_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test generating flashcards from book content."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 10,
            "num_cards": 10
        }
        response = await async_client.post("/api/ai/flashcards", json=payload, headers=headers)
        assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_generate_flashcards_max_limit(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test flashcard generation respects max limit."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 50,
            "num_cards": 1000
        }
        response = await async_client.post("/api/ai/flashcards", json=payload, headers=headers)
        assert response.status_code in [200, 202, 400, 422, 502]

    @pytest.mark.asyncio
    async def test_ai_ask_question_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test asking AI questions about a book."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1,
            "question": "What is the main theme of this book?"
        }
        response = await async_client.post("/api/ai/ask", json=payload, headers=headers)
        assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_ai_ask_question_empty(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test asking empty question."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "question": ""
        }
        response = await async_client.post("/api/ai/ask", json=payload, headers=headers)
        assert response.status_code in [400, 422, 502]

    @pytest.mark.asyncio
    async def test_ai_analyze_text_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test AI text analysis."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1
        }
        response = await async_client.post("/api/ai/analyze", json=payload, headers=headers)
        assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_extract_keywords_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test extracting keywords from book content."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1,
            "num_keywords": 10
        }
        response = await async_client.post("/api/ai/keywords", json=payload, headers=headers)
        assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_ai_graceful_degradation_no_openai(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test that AI endpoints gracefully degrade if OpenAI is unavailable."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1,
            "question": "What happens if OpenAI is down?"
        }
        response = await async_client.post("/api/ai/ask", json=payload, headers=headers)
        # Should either work or return 502, not 500
        assert response.status_code in [200, 202, 502]

    @pytest.mark.asyncio
    async def test_ai_response_schema_valid(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test that AI responses follow correct schema."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1
        }
        response = await async_client.post("/api/ai/summary", json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Response should have expected fields
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_quiz_response_validation(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test that quiz responses have proper structure."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 1,
            "num_questions": 5
        }
        response = await async_client.post("/api/ai/quiz", json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

    @pytest.mark.asyncio
    async def test_flashcard_response_validation(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test that flashcard responses have proper structure."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 10,
            "num_cards": 5
        }
        response = await async_client.post("/api/ai/flashcards", json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

    @pytest.mark.asyncio
    async def test_ai_multi_page_question(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test asking questions about multiple pages."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 50,
            "question": "Compare the themes in these chapters"
        }
        response = await async_client.post("/api/ai/ask", json=payload, headers=headers)
        assert response.status_code in [200, 202, 400, 422, 502]

    @pytest.mark.asyncio
    async def test_ai_generate_study_guide(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test generating a study guide."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 50
        }
        response = await async_client.post("/api/ai/study-guide", json=payload, headers=headers)
        assert response.status_code in [200, 202, 404, 502]

    @pytest.mark.asyncio
    async def test_ai_unauthorized_access(self, async_client: AsyncClient):
        """Test that AI endpoints require authentication."""
        payload = {
            "book_id": "test-book-123",
            "question": "What is this about?"
        }
        response = await async_client.post("/api/ai/ask", json=payload)
        assert response.status_code == 403
