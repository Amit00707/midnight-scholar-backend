"""
Teacher Routes — /classes /assign /quiz-results /announce
===========================================================
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.database.models.user import User

router = APIRouter()


@router.get("/classes")
async def get_my_classes(user: User = Depends(get_current_user)):
    """Get all classes managed by the teacher."""
    if user.role != "teacher":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Teacher access required")
    # TODO: Query classes table
    return {"classes": []}


@router.post("/assign")
async def create_assignment(user: User = Depends(get_current_user)):
    """Assign a book/quiz to a class."""
    if user.role != "teacher":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Teacher access required")
    # TODO: Create assignment record
    return {"message": "Assignment created"}


@router.get("/quiz-results")
async def get_quiz_results(user: User = Depends(get_current_user)):
    """Get aggregated quiz results for a class."""
    if user.role != "teacher":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Teacher access required")
    return {"results": []}


@router.post("/announce")
async def send_announcement(user: User = Depends(get_current_user)):
    """Send an announcement to all students in a class."""
    if user.role != "teacher":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Teacher access required")
    return {"message": "Announcement sent"}
