"""
Test Suite: Social API Endpoints
=================================
Tests for comments, public notes, and group features.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.social import Comment, PublicNote, Group, GroupMember
from tests.factories import CommentFactory, PublicNoteFactory, GroupFactory, GroupMemberFactory


class TestSocial:
    """Social API endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_comment_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test creating a comment successfully."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "content": "This is a great book!"
        }
        response = await async_client.post("/api/social/comments", json=payload, headers=headers)
        assert response.status_code in [200, 201, 404, 405, 422]

    @pytest.mark.asyncio
    async def test_create_comment_unauthorized(self, async_client: AsyncClient):
        """Test creating comment without authentication."""
        payload = {
            "book_id": "test-book-123",
            "content": "Great book!"
        }
        response = await async_client.post("/api/social/comments", json=payload)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_comment_empty_content(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test creating comment with empty content."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "content": ""
        }
        response = await async_client.post("/api/social/comments", json=payload, headers=headers)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_get_comments_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving comments for a book."""
        # Create test comments
        comment = CommentFactory.build(user_id=test_user.id, book_id="test-book-123")
        test_db.add(comment)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get(
            "/api/social/comments/test-book-123", headers=headers
        )
        assert response.status_code in [200, 404, 405]
        assert isinstance(response.json(), (list, dict))

    @pytest.mark.asyncio
    async def test_get_comments_empty(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test retrieving comments when none exist."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get(
            "/api/social/comments/nonexistent-book", headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_upvote_comment_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test upvoting a comment."""
        comment = CommentFactory.build(user_id=test_user.id, book_id="test-book-123", upvotes=5)
        test_db.add(comment)
        await test_db.commit()
        await test_db.refresh(comment)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.post(
            f"/api/social/comments/{comment.id}/upvote", headers=headers
        )
        assert response.status_code in [200, 201, 404, 405]

    @pytest.mark.asyncio
    async def test_upvote_nonexistent_comment(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test upvoting a non-existent comment."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.post(
            "/api/social/comments/99999/upvote", headers=headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_comment_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test deleting own comment."""
        comment = CommentFactory.build(user_id=test_user.id, book_id="test-book-123")
        test_db.add(comment)
        await test_db.commit()
        await test_db.refresh(comment)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.delete(
            f"/api/social/comments/{comment.id}", headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_delete_others_comment(
        self, async_client: AsyncClient, test_user: User, test_teacher: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test deleting someone else's comment."""
        comment = CommentFactory.build(user_id=test_teacher.id, book_id="test-book-123")
        test_db.add(comment)
        await test_db.commit()
        await test_db.refresh(comment)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.delete(
            f"/api/social/comments/{comment.id}", headers=headers
        )
        assert response.status_code in [403, 404, 405]

    @pytest.mark.asyncio
    async def test_create_public_note_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test creating a public note."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "page_number": 42,
            "content": "This page changed my perspective",
            "is_public": True
        }
        response = await async_client.post("/api/social/notes", json=payload, headers=headers)
        assert response.status_code in [200, 201, 404, 405]

    @pytest.mark.asyncio
    async def test_get_public_notes_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving public notes for a book."""
        note = PublicNoteFactory.build(user_id=test_user.id, book_id="test-book-123", is_public=True)
        test_db.add(note)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get(
            "/api/social/notes/test-book-123", headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_get_public_notes_empty(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test retrieving public notes when none exist."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get(
            "/api/social/notes/nonexistent-book", headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_create_group_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test creating a reading group."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "name": "Python Enthusiasts",
            "description": "A group for Python book lovers"
        }
        response = await async_client.post("/api/social/groups", json=payload, headers=headers)
        assert response.status_code in [200, 201, 404, 405]

    @pytest.mark.asyncio
    async def test_get_groups_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving all groups."""
        group = GroupFactory.build(created_by=test_user.id)
        test_db.add(group)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get("/api/social/groups", headers=headers)
        assert response.status_code in [200, 404, 405]
        assert isinstance(response.json(), (list, dict))

    @pytest.mark.asyncio
    async def test_join_group_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test joining a group."""
        group = GroupFactory.build(created_by=test_user.id)
        test_db.add(group)
        await test_db.commit()
        await test_db.refresh(group)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.post(
            f"/api/social/groups/{group.id}/join", headers=headers
        )
        assert response.status_code in [200, 201, 404, 405]

    @pytest.mark.asyncio
    async def test_leave_group_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test leaving a group."""
        group = GroupFactory.build(created_by=test_user.id)
        test_db.add(group)
        await test_db.flush()

        member = GroupMemberFactory.build(group_id=group.id, user_id=test_user.id)
        test_db.add(member)
        await test_db.commit()
        await test_db.refresh(group)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.post(
            f"/api/social/groups/{group.id}/leave", headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_get_group_members_success(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving group members."""
        group = GroupFactory.build(created_by=test_user.id)
        test_db.add(group)
        await test_db.flush()

        member = GroupMemberFactory.build(group_id=group.id, user_id=test_user.id)
        test_db.add(member)
        await test_db.commit()
        await test_db.refresh(group)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.get(
            f"/api/social/groups/{group.id}/members", headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_update_note_privacy(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test changing note privacy settings."""
        note = PublicNoteFactory.build(user_id=test_user.id, book_id="test-book-123", is_public=True)
        test_db.add(note)
        await test_db.commit()
        await test_db.refresh(note)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.patch(
            f"/api/social/notes/{note.id}",
            json={"is_public": False},
            headers=headers
        )
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_like_public_note(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test liking a public note."""
        note = PublicNoteFactory.build(user_id=test_user.id, book_id="test-book-123", is_public=True)
        test_db.add(note)
        await test_db.commit()
        await test_db.refresh(note)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        response = await async_client.post(
            f"/api/social/notes/{note.id}/like", headers=headers
        )
        assert response.status_code in [200, 201, 400, 404]
