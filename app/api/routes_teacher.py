"""
Teacher Routes — /classes /assign /quiz-results /announce
===========================================================
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.database.models.user import User
from app.database.models.teacher import Classroom, StudentEnrollment, Assignment, Announcement
from app.schemas.teacher import ClassroomCreate, ClassroomResponse, AssignmentCreate, AnnouncementCreate

router = APIRouter()

def require_teacher(user: User):
    if getattr(user.role, "value", user.role) != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")


@router.get("/classes")
async def get_my_classes(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all classes managed by the teacher."""
    require_teacher(user)
    
    result = await db.execute(
        select(Classroom)
        .where(Classroom.teacher_id == user.id)
        .order_by(desc(Classroom.created_at))
    )
    classes = result.scalars().all()
    return {"classes": classes}


@router.post("/classes")
async def create_class(payload: ClassroomCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a new classroom."""
    require_teacher(user)
    
    classroom = Classroom(name=payload.name, description=payload.description, teacher_id=user.id)
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)
    return classroom


@router.post("/classes/{class_id}/enroll")
async def enroll_student(class_id: int, student_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Enroll a student in a class."""
    require_teacher(user)
    
    # Verify class belongs to teacher
    cls_result = await db.execute(select(Classroom).where(Classroom.id == class_id, Classroom.teacher_id == user.id))
    if not cls_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Classroom not found")

    enrollment = StudentEnrollment(class_id=class_id, student_id=student_id)
    db.add(enrollment)
    await db.commit()
    return {"message": f"Student {student_id} enrolled successfully"}


@router.post("/classes/{class_id}/assign")
async def create_assignment(class_id: int, payload: AssignmentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Assign a book to a class."""
    require_teacher(user)
    
    assignment = Assignment(
        class_id=class_id,
        book_id=payload.book_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date
    )
    db.add(assignment)
    await db.commit()
    return {"message": "Assignment created successfully"}


@router.post("/classes/{class_id}/announce")
async def send_announcement(class_id: int, payload: AnnouncementCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Send an announcement to all students in a class."""
    require_teacher(user)
    
    announcement = Announcement(
        class_id=class_id,
        title=payload.title,
        content=payload.content
    )
    db.add(announcement)
    await db.commit()
    return {"message": "Announcement sent"}


@router.get("/quiz-results")
async def get_quiz_results(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get aggregated quiz results for a class."""
    require_teacher(user)
    # Placeholder for a complex join query on reading progress/quiz scores
    return {"results": []}
