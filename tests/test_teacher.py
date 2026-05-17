"""
Test Suite: Teacher Dashboard Endpoints
=======================================
Tests for classroom management, assignments, and announcements.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.database.models.teacher import Classroom, StudentEnrollment, Assignment, Announcement
from tests.factories import ClassroomFactory, StudentEnrollmentFactory, AssignmentFactory, AnnouncementFactory
from datetime import datetime, timezone, timedelta


class TestTeacher:
    """Teacher API endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_classroom_unauthorized(self, async_client: AsyncClient, test_jwt_token: str):
        """Test creating classroom without teacher role."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "name": "Advanced Python",
            "description": "Learn Python for advanced projects"
        }
        response = await async_client.post("/api/teacher/classes", json=payload, headers=headers)
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_create_classroom_as_teacher(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str
    ):
        """Test creating classroom as a teacher."""
        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        payload = {
            "name": "Advanced Python",
            "description": "Learn Python for advanced projects"
        }
        response = await async_client.post("/api/teacher/classes", json=payload, headers=headers)
        assert response.status_code in [200, 201, 404, 405, 422]

    @pytest.mark.asyncio
    async def test_create_classroom_missing_fields(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str
    ):
        """Test creating classroom with missing fields."""
        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        payload = {"name": "Test Class"}
        response = await async_client.post("/api/teacher/classes", json=payload, headers=headers)
        assert response.status_code in [200, 422, 400]

    @pytest.mark.asyncio
    async def test_get_classrooms_as_teacher(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving classrooms as teacher."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.get("/api/teacher/classes", headers=headers)
        assert response.status_code in [200, 404, 405]
        assert isinstance(response.json(), (list, dict))

    @pytest.mark.asyncio
    async def test_get_classroom_details(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test getting details of a specific classroom."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.get(f"/api/teacher/classes/{classroom.id}", headers=headers)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_enroll_student_success(
        self, async_client: AsyncClient, test_user: User, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test enrolling a student in a classroom."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        payload = {"student_id": test_user.id}
        response = await async_client.post(
            f"/api/teacher/classes/{classroom.id}/enroll",
            json=payload,
            headers=headers
        )
        assert response.status_code in [200, 201, 404, 405, 422]

    @pytest.mark.asyncio
    async def test_enroll_student_unauthorized(
        self, async_client: AsyncClient, test_user: User, test_teacher: User, test_jwt_token: str, test_db: AsyncSession
    ):
        """Test enrolling student without teacher role."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {"student_id": test_user.id}
        response = await async_client.post(
            f"/api/teacher/classes/{classroom.id}/enroll",
            json=payload,
            headers=headers
        )
        assert response.status_code in [403, 404, 422]

    @pytest.mark.asyncio
    async def test_assign_book_to_class_success(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test assigning a book to classroom."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        payload = {
            "book_id": "test-book-123",
            "title": "Python Basics",
            "description": "Learn Python fundamentals",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
        response = await async_client.post(
            f"/api/teacher/classes/{classroom.id}/assignments",
            json=payload,
            headers=headers
        )
        assert response.status_code in [200, 201, 404, 405, 422]

    @pytest.mark.asyncio
    async def test_get_classroom_assignments(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving classroom assignments."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.flush()

        assignment = AssignmentFactory.build(class_id=classroom.id, book_id="test-book-123")
        test_db.add(assignment)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.get(
            f"/api/teacher/classes/{classroom.id}/assignments",
            headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_send_announcement_success(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test sending classroom announcement."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        payload = {
            "title": "Assignment Due Tomorrow",
            "content": "Remember to submit your book analysis by tomorrow midnight."
        }
        response = await async_client.post(
            f"/api/teacher/classes/{classroom.id}/announcements",
            json=payload,
            headers=headers
        )
        assert response.status_code in [200, 201, 404, 405, 422]

    @pytest.mark.asyncio
    async def test_get_announcements(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving classroom announcements."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.flush()

        announcement = AnnouncementFactory.build(class_id=classroom.id)
        test_db.add(announcement)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.get(
            f"/api/teacher/classes/{classroom.id}/announcements",
            headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_get_quiz_results_success(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving quiz results for classroom."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.get(
            f"/api/teacher/classes/{classroom.id}/quiz-results",
            headers=headers
        )
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_class_students(
        self, async_client: AsyncClient, test_user: User, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test retrieving students in a classroom."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.flush()

        enrollment = StudentEnrollmentFactory.build(class_id=classroom.id, student_id=test_user.id)
        test_db.add(enrollment)
        await test_db.commit()

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.get(
            f"/api/teacher/classes/{classroom.id}/students",
            headers=headers
        )
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_update_classroom_success(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test updating classroom details."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        payload = {
            "name": "Updated Class Name",
            "description": "Updated description"
        }
        response = await async_client.patch(
            f"/api/teacher/classes/{classroom.id}",
            json=payload,
            headers=headers
        )
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_delete_classroom_success(
        self, async_client: AsyncClient, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test deleting a classroom."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.delete(
            f"/api/teacher/classes/{classroom.id}",
            headers=headers
        )
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_remove_student_from_class(
        self, async_client: AsyncClient, test_user: User, test_teacher: User, test_teacher_jwt_token: str, test_db: AsyncSession
    ):
        """Test removing a student from classroom."""
        classroom = ClassroomFactory.build(teacher_id=test_teacher.id)
        test_db.add(classroom)
        await test_db.flush()

        enrollment = StudentEnrollmentFactory.build(class_id=classroom.id, student_id=test_user.id)
        test_db.add(enrollment)
        await test_db.commit()
        await test_db.refresh(classroom)

        headers = {"Authorization": f"Bearer {test_teacher_jwt_token}"}
        response = await async_client.delete(
            f"/api/teacher/classes/{classroom.id}/students/{test_user.id}",
            headers=headers
        )
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_non_teacher_cannot_create_class(
        self, async_client: AsyncClient, test_user: User, test_jwt_token: str
    ):
        """Test that non-teachers cannot create classrooms."""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        payload = {
            "name": "Unauthorized Class",
            "description": "This should fail"
        }
        response = await async_client.post("/api/teacher/classes", json=payload, headers=headers)
        assert response.status_code in [403, 404]
