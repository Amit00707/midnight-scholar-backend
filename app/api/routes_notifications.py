"""
Notification Routes — /notifications /preferences
=====================================================
Handles user notification operations and preferences management.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.database.models.user import User
from app.database.models.notification import (
    Notification,
    NotificationPreference,
    NotificationChannelEnum,
)
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationTestRequest,
)
from app.services.notification_service import (
    get_user_preferences,
    should_send_notification,
    store_notification,
    send_in_app_notification,
    clear_user_preferences_cache,
)
from app.services.email_service import send_email, email_service
from app.services.push_service import send_push, push_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    read_status: Optional[str] = Query(None, description="Filter: 'read', 'unread', or None for all"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
) -> NotificationListResponse:
    """
    Get paginated notifications for the current user.

    Query parameters:
    - read_status: 'read', 'unread', or None (all)
    - notification_type: Filter by type (optional)
    - skip, limit: Pagination
    """
    # Build query
    query = select(Notification).where(Notification.user_id == user.id)

    # Filter by read status
    if read_status == "read":
        query = query.where(Notification.is_read == True)
    elif read_status == "unread":
        query = query.where(Notification.is_read == False)

    # Filter by type
    if notification_type:
        query = query.where(Notification.notification_type == notification_type)

    # Count total
    count_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == user.id)
    )
    total = count_result.scalar()

    # Order by created_at desc and paginate
    query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    # Convert to response schemas
    notification_responses = [
        NotificationResponse.model_validate(n) for n in notifications
    ]

    return NotificationListResponse(
        notifications=notification_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/notifications/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Get count of unread notifications for the current user."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user.id,
                Notification.is_read == False,
            )
        )
    )
    unread_count = result.scalar() or 0
    return UnreadCountResponse(unread_count=unread_count)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Verify ownership
    if notification.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' notifications",
        )

    # Mark as read
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.commit()
    await db.refresh(notification)

    logger.info(f"Marked notification {notification_id} as read for user {user.id}")
    return NotificationResponse.model_validate(notification)


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a notification."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Verify ownership
    if notification.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other users' notifications",
        )

    await db.delete(notification)
    await db.commit()

    logger.info(f"Deleted notification {notification_id} for user {user.id}")


@router.get("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """Get user's notification preferences (creates default if not exists)."""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()

    # Create default if not exists
    if pref is None:
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
        logger.info(f"Created default notification preferences for user {user.id}")

    return NotificationPreferenceResponse.model_validate(pref)


@router.put("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    update_data: NotificationPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """Update user's notification preferences (supports partial updates)."""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()

    # Create if not exists
    if pref is None:
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            setattr(pref, key, value)

    await db.commit()
    await db.refresh(pref)

    # Clear cache for this user
    await clear_user_preferences_cache(user.id)

    logger.info(f"Updated notification preferences for user {user.id}")
    return NotificationPreferenceResponse.model_validate(pref)


@router.post("/notifications/test", response_model=dict)
async def send_test_notification(
    test_request: NotificationTestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Send a test notification to verify user's preferences and settings.
    Admins can test for any user, regular users test for themselves.
    """
    # For now, allow all users to test for themselves
    # Admins could test for others (not implemented)

    channel = test_request.channel.lower()
    if channel not in ["email", "push", "in_app"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel must be 'email', 'push', or 'in_app'",
        )

    # Send test in-app notification (always possible)
    if channel == "in_app":
        success = await send_in_app_notification(
            user_id=user.id,
            notif_type="announcement",  # Use generic type
            title=test_request.title,
            body=test_request.body,
            db=db,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send test notification (preferences may be disabled)",
            )
        return {
            "status": "success",
            "message": f"Test {channel} notification sent to user {user.id}",
            "channel": channel,
        }

    # For email/push, check preferences first
    if not await should_send_notification(user.id, "announcement", channel, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{channel.capitalize()} notifications are disabled in your preferences or you're in quiet hours",
        )

    # Store notification in database first
    await store_notification(
        user_id=user.id,
        notif_type="announcement",
        channel=channel,
        title=test_request.title,
        body=test_request.body,
        recipient_email=user.email if channel == "email" else None,
        db=db,
    )

    # Actually send the notification via email or push
    if channel == "email" and user.email:
        if email_service.is_configured:
            await send_email(
                to_email=user.email,
                subject=test_request.title,
                body=test_request.body,
            )
            logger.info(f"Sent test email to {user.email}")
        else:
            logger.info(f"Email service not configured - email logged but not sent")
            return {
                "status": "success",
                "message": f"Test {channel} notification stored (email service not configured)",
                "channel": channel,
                "warning": "Email service not configured - set SENDGRID_API_KEY in .env",
            }

    elif channel == "push" and test_request.fcm_token:
        if push_service.is_configured:
            await send_push(
                fcm_token=test_request.fcm_token,
                title=test_request.title,
                body=test_request.body,
            )
            logger.info(f"Sent test push to token")
        else:
            logger.info(f"Push service not configured - notification stored but not sent")

    logger.info(f"Sent test {channel} notification to user {user.id}")
    return {
        "status": "success",
        "message": f"Test {channel} notification sent to user {user.id}",
        "channel": channel,
    }
