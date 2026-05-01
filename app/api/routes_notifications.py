"""
Notification Routes — /notifications /preferences
=====================================================
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.database.models.user import User

router = APIRouter()


@router.get("/notifications")
async def get_notifications(user: User = Depends(get_current_user)):
    """Get all notifications for the current user."""
    # TODO: Query notifications table
    return {"notifications": []}


@router.put("/notifications/preferences")
async def update_preferences(user: User = Depends(get_current_user)):
    """Update notification preferences (email, push, in-app)."""
    return {"message": "Preferences updated"}
