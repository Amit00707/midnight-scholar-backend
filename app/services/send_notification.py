"""
Notification Sender — Unified Interface for Email & Push
========================================================
Combines email and push services for easy sending.
"""

import logging
from typing import Optional, Dict, Any

from app.services.email_service import (
    send_email,
    send_welcome_email,
    send_streak_reminder_email,
    send_achievement_email,
    email_service,
)
from app.services.push_service import (
    send_push,
    send_streak_reminder_push,
    send_achievement_push,
    send_flashcard_due_push,
    send_class_assignment_push,
    push_service,
)

logger = logging.getLogger(__name__)


async def send_user_notification(
    user_id: int,
    user_email: str,
    fcm_token: Optional[str],
    notification_type: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Send notification to user via all enabled channels.

    Args:
        user_id: User ID
        user_email: User's email address
        fcm_token: User's FCM token (optional)
        notification_type: Type of notification
        title: Notification title
        body: Notification body
        data: Additional data payload

    Returns:
        dict with status of each channel: {"email": "sent/failed/skipped", "push": "sent/failed/skipped"}
    """
    results = {"email": "skipped", "push": "skipped"}

    # Send email if service is configured
    if email_service.is_configured and user_email:
        try:
            success = await send_email(user_email, title, body)
            results["email"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send email to user {user_id}: {e}")
            results["email"] = "failed"
    else:
        logger.debug(f"Email not sent - service not configured or no email for user {user_id}")

    # Send push if service is configured and token provided
    if push_service.is_configured and fcm_token:
        try:
            success = await send_push(fcm_token, title, body, data)
            results["push"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send push to user {user_id}: {e}")
            results["push"] = "failed"
    else:
        logger.debug(f"Push not sent - service not configured or no token for user {user_id}")

    return results


# Quick send functions for common notifications
async def notify_user_welcome(user_id: int, user_email: str, user_name: str) -> Dict[str, str]:
    """Send welcome notification to new user."""
    if not user_email:
        return {"email": "skipped", "push": "skipped"}

    if not email_service.is_configured:
        logger.info(f"Would send welcome email to {user_email}")
        return {"email": "skipped", "push": "skipped"}

    try:
        success = await send_welcome_email(user_email, user_name)
        return {"email": "sent" if success else "failed", "push": "skipped"}
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")
        return {"email": "failed", "push": "skipped"}


async def notify_streak_reminder(
    user_id: int,
    user_email: str,
    fcm_token: Optional[str],
    user_name: str,
    streak_days: int,
) -> Dict[str, str]:
    """Send streak reminder notification."""
    results = {"email": "skipped", "push": "skipped"}

    if email_service.is_configured and user_email:
        try:
            success = await send_streak_reminder_email(user_email, user_name, streak_days)
            results["email"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send streak email: {e}")

    if push_service.is_configured and fcm_token:
        try:
            success = await send_streak_reminder_push(fcm_token, streak_days)
            results["push"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send streak push: {e}")

    return results


async def notify_achievement_earned(
    user_id: int,
    user_email: str,
    fcm_token: Optional[str],
    user_name: str,
    badge_name: str,
    badge_icon: str,
) -> Dict[str, str]:
    """Send achievement earned notification."""
    results = {"email": "skipped", "push": "skipped"}

    if email_service.is_configured and user_email:
        try:
            success = await send_achievement_email(user_email, user_name, badge_name, badge_icon)
            results["email"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send achievement email: {e}")

    if push_service.is_configured and fcm_token:
        try:
            success = await send_achievement_push(fcm_token, badge_name, badge_icon)
            results["push"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send achievement push: {e}")

    return results


async def notify_flashcards_due(
    user_id: int,
    user_email: str,
    fcm_token: Optional[str],
    due_count: int,
) -> Dict[str, str]:
    """Send flashcard due reminder notification."""
    results = {"email": "skipped", "push": "skipped"}

    if push_service.is_configured and fcm_token:
        try:
            success = await send_flashcard_due_push(fcm_token, due_count)
            results["push"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send flashcard push: {e}")

    return results


async def notify_class_assignment(
    user_id: int,
    user_email: str,
    fcm_token: Optional[str],
    class_name: str,
    book_title: str,
    due_date: str,
) -> Dict[str, str]:
    """Send class assignment notification."""
    results = {"email": "skipped", "push": "skipped"}

    if push_service.is_configured and fcm_token:
        try:
            success = await send_class_assignment_push(fcm_token, class_name, book_title, due_date)
            results["push"] = "sent" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send class assignment push: {e}")

    return results


# Check if notifications are configured
def are_notifications_configured() -> Dict[str, bool]:
    """Check which notification channels are configured."""
    return {
        "email": email_service.is_configured,
        "push": push_service.is_configured,
    }