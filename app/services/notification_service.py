"""
Notification Service — Smart Reminders + Streak Alerts + Full Implementation
===============================================================================
Handles sending notifications via email, push, and in-app channels.
Checks user preferences, caches data, enforces quiet hours, and manages rate limiting.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory
from app.database.models.notification import (
    Notification,
    NotificationPreference,
    NotificationTemplate,
    NotificationTypeEnum,
    NotificationChannelEnum,
)
from app.core.redis_client import cache_get, cache_set, cache_incr, cache_exists
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache key templates
PREF_CACHE_KEY = "notif_pref:user:{user_id}"
RATE_LIMIT_KEY = "notif_ratelimit:{user_id}:{notif_type}"


async def get_user_preferences(user_id: int, db: Optional[AsyncSession] = None) -> NotificationPreference:
    """
    Fetch user's notification preferences from cache or database.
    Creates default preferences if user doesn't have any.
    """
    cache_key = PREF_CACHE_KEY.format(user_id=user_id)

    # Try cache first
    cached = cache_get(cache_key)
    if cached:
        logger.debug(f"Preferences cache hit for user {user_id}")
        return cached

    # Fetch from DB
    should_close = False
    if db is None:
        session_factory = get_session_factory()
        db = session_factory()
        should_close = True

    try:
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        # Create default if not exists
        if pref is None:
            pref = NotificationPreference(user_id=user_id)
            db.add(pref)
            await db.commit()
            logger.info(f"Created default notification preferences for user {user_id}")

        # Convert to dict for caching
        pref_dict = {
            "id": pref.id,
            "user_id": pref.user_id,
            "email_enabled": pref.email_enabled,
            "push_enabled": pref.push_enabled,
            "in_app_enabled": pref.in_app_enabled,
            "streak_reminders": pref.streak_reminders,
            "quiz_alerts": pref.quiz_alerts,
            "achievements": pref.achievements,
            "messages": pref.messages,
            "reading_reminders": pref.reading_reminders,
            "announcements": pref.announcements,
            "class_assignments": pref.class_assignments,
            "comment_replies": pref.comment_replies,
            "quiet_hours_enabled": pref.quiet_hours_enabled,
            "quiet_hours_start": pref.quiet_hours_start,
            "quiet_hours_end": pref.quiet_hours_end,
            "digest_frequency": pref.digest_frequency,
        }

        # Cache for 1 hour
        cache_set(cache_key, pref_dict, ttl=3600)
        return pref_dict

    finally:
        if should_close:
            await db.close()


def _is_in_quiet_hours(prefs: Dict[str, Any]) -> bool:
    """Check if current time is within quiet hours."""
    if not prefs.get("quiet_hours_enabled"):
        return False

    now = datetime.utcnow()
    current_time = now.time()

    start_str = prefs.get("quiet_hours_start", "22:00")
    end_str = prefs.get("quiet_hours_end", "08:00")

    # Parse times
    try:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
    except ValueError:
        logger.warning(f"Invalid quiet hours format: {start_str} - {end_str}")
        return False

    # Handle wraparound (e.g., 22:00 to 08:00 crosses midnight)
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return current_time >= start_time or current_time <= end_time


def _is_rate_limited(user_id: int, notif_type: str, max_per_hour: int = 5) -> bool:
    """Check rate limiting — prevent notification spam."""
    key = RATE_LIMIT_KEY.format(user_id=user_id, notif_type=notif_type)
    count = cache_incr(key, ttl=3600)
    is_limited = count > max_per_hour
    if is_limited:
        logger.warning(f"Rate limit exceeded for user {user_id}, type {notif_type}")
    return is_limited


async def should_send_notification(
    user_id: int, notif_type: str, channel: str, db: Optional[AsyncSession] = None
) -> bool:
    """
    Determine whether a notification should be sent based on:
    - User preferences for this type + channel
    - Quiet hours
    - Rate limiting
    """
    prefs = await get_user_preferences(user_id, db)

    # Check channel enabled
    channel_enabled_key = f"{channel}_enabled"
    if not prefs.get(channel_enabled_key, False):
        logger.debug(f"Channel {channel} disabled for user {user_id}")
        return False

    # Check notification type enabled
    notif_type_key = _map_notif_type_to_pref_key(notif_type)
    if notif_type_key and not prefs.get(notif_type_key, False):
        logger.debug(f"Notification type {notif_type} disabled for user {user_id}")
        return False

    # Check quiet hours
    if channel == "push" or channel == "email":  # In-app can always be sent
        if _is_in_quiet_hours(prefs):
            logger.debug(f"In quiet hours for user {user_id}")
            return False

    # Check rate limiting
    if _is_rate_limited(user_id, notif_type):
        logger.debug(f"Rate limited for user {user_id}, type {notif_type}")
        return False

    return True


def _map_notif_type_to_pref_key(notif_type: str) -> Optional[str]:
    """Map notification type to preference key."""
    mapping = {
        NotificationTypeEnum.STREAK_REMINDER.value: "streak_reminders",
        NotificationTypeEnum.QUIZ_DUE.value: "quiz_alerts",
        NotificationTypeEnum.ACHIEVEMENT.value: "achievements",
        NotificationTypeEnum.MESSAGE.value: "messages",
        NotificationTypeEnum.READING_REMINDER.value: "reading_reminders",
        NotificationTypeEnum.ANNOUNCEMENT.value: "announcements",
        NotificationTypeEnum.CLASS_ASSIGNMENT.value: "class_assignments",
        NotificationTypeEnum.COMMENT_REPLY.value: "comment_replies",
    }
    return mapping.get(notif_type)


def _format_template(template_text: str, variables: Dict[str, Any]) -> str:
    """Format template text with variables. E.g., 'Hi {user_name}' with {'user_name': 'John'}."""
    if not variables:
        return template_text
    try:
        return template_text.format(**variables)
    except KeyError as e:
        logger.warning(f"Missing template variable: {e}")
        return template_text


async def get_notification_template(
    notif_type: str, db: Optional[AsyncSession] = None
) -> Optional[NotificationTemplate]:
    """Fetch notification template from database."""
    should_close = False
    if db is None:
        session_factory = get_session_factory()
        db = session_factory()
        should_close = True

    try:
        result = await db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.notification_type == notif_type
            )
        )
        return result.scalar_one_or_none()
    finally:
        if should_close:
            await db.close()


async def store_notification(
    user_id: int,
    notif_type: str,
    channel: str,
    title: str,
    body: str,
    recipient_email: Optional[str] = None,
    fcm_token: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Optional[Notification]:
    """Store notification in database."""
    should_close = False
    if db is None:
        session_factory = get_session_factory()
        db = session_factory()
        should_close = True

    try:
        notif = Notification(
            user_id=user_id,
            notification_type=notif_type,
            channel=channel,
            title=title,
            body=body,
            recipient_email=recipient_email,
            fcm_token=fcm_token,
            sent_at=datetime.utcnow(),
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        logger.info(f"Stored notification {notif.id} for user {user_id}")
        return notif
    except Exception as e:
        logger.error(f"Failed to store notification: {e}")
        return None
    finally:
        if should_close:
            await db.close()


async def queue_notification_tasks(
    user_id: int,
    notif_type: str,
    channel: str,
    title: str,
    body: str,
    recipient_email: Optional[str] = None,
    fcm_token: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
) -> bool:
    """Queue background tasks for sending notifications via Celery."""
    try:
        from app.workers.celery_app import celery_app

        if channel == "email" and recipient_email:
            # Queue email task
            celery_app.send_task(
                "send_email_task",
                args=(recipient_email, title, body),
                kwargs={"html_body": None},
            )
            logger.info(f"Queued email task for {recipient_email}")

        elif channel == "push" and fcm_token:
            # Queue push task
            celery_app.send_task(
                "send_push_task",
                args=(fcm_token, title, body),
                kwargs={"data": template_vars or {}},
            )
            logger.info(f"Queued push task for FCM token {fcm_token[:20]}...")

        return True
    except Exception as e:
        logger.error(f"Failed to queue notification tasks: {e}")
        return False


async def send_streak_reminder(user_id: int, streak_count: int = 0, db: Optional[AsyncSession] = None):
    """Send a reminder to maintain reading streak."""
    if not await should_send_notification(user_id, NotificationTypeEnum.STREAK_REMINDER.value, "email", db):
        logger.debug(f"Streak reminder skipped for user {user_id} (preferences)")
        return

    # Get template
    template = await get_notification_template(NotificationTypeEnum.STREAK_REMINDER.value, db)
    if not template:
        logger.warning(f"No template for streak_reminder")
        return

    # Prepare variables for template
    template_vars = {
        "streak_count": streak_count,
        "user_name": f"User {user_id}",  # In real use, fetch from DB
    }

    # Format templates
    email_subject = _format_template(template.email_subject, template_vars)
    email_body = _format_template(template.email_body, template_vars)
    push_title = _format_template(template.push_title, template_vars)
    push_body = _format_template(template.push_body, template_vars)
    in_app_title = _format_template(template.in_app_title, template_vars)
    in_app_body = _format_template(template.in_app_body, template_vars)

    # Get user email (mock for now)
    recipient_email = f"user{user_id}@example.com"

    # Send via email and in-app
    await store_notification(
        user_id=user_id,
        notif_type=NotificationTypeEnum.STREAK_REMINDER.value,
        channel="email",
        title=email_subject,
        body=email_body,
        recipient_email=recipient_email,
        db=db,
    )

    await store_notification(
        user_id=user_id,
        notif_type=NotificationTypeEnum.STREAK_REMINDER.value,
        channel="in_app",
        title=in_app_title,
        body=in_app_body,
        db=db,
    )

    # Queue background tasks
    await queue_notification_tasks(
        user_id=user_id,
        notif_type=NotificationTypeEnum.STREAK_REMINDER.value,
        channel="email",
        title=email_subject,
        body=email_body,
        recipient_email=recipient_email,
        template_vars=template_vars,
    )

    logger.info(f"✓ Streak reminder sent to user {user_id}")


async def send_quiz_due_alert(user_id: int, quiz_name: str, db: Optional[AsyncSession] = None):
    """Alert student about an upcoming quiz deadline."""
    if not await should_send_notification(user_id, NotificationTypeEnum.QUIZ_DUE.value, "email", db):
        logger.debug(f"Quiz alert skipped for user {user_id}")
        return

    template = await get_notification_template(NotificationTypeEnum.QUIZ_DUE.value, db)
    if not template:
        logger.warning("No template for quiz_due")
        return

    template_vars = {"quiz_name": quiz_name}

    email_subject = _format_template(template.email_subject, template_vars)
    email_body = _format_template(template.email_body, template_vars)
    in_app_title = _format_template(template.in_app_title, template_vars)
    in_app_body = _format_template(template.in_app_body, template_vars)

    recipient_email = f"user{user_id}@example.com"

    await store_notification(
        user_id=user_id,
        notif_type=NotificationTypeEnum.QUIZ_DUE.value,
        channel="email",
        title=email_subject,
        body=email_body,
        recipient_email=recipient_email,
        db=db,
    )

    await store_notification(
        user_id=user_id,
        notif_type=NotificationTypeEnum.QUIZ_DUE.value,
        channel="in_app",
        title=in_app_title,
        body=in_app_body,
        db=db,
    )

    await queue_notification_tasks(
        user_id=user_id,
        notif_type=NotificationTypeEnum.QUIZ_DUE.value,
        channel="email",
        title=email_subject,
        body=email_body,
        recipient_email=recipient_email,
        template_vars=template_vars,
    )

    logger.info(f"✓ Quiz alert sent to user {user_id} for '{quiz_name}'")


async def send_achievement_notification(
    user_id: int, badge_name: str, description: str = "", db: Optional[AsyncSession] = None
):
    """Notify user about a new badge earned."""
    if not await should_send_notification(user_id, NotificationTypeEnum.ACHIEVEMENT.value, "in_app", db):
        logger.debug(f"Achievement notification skipped for user {user_id}")
        return

    template = await get_notification_template(NotificationTypeEnum.ACHIEVEMENT.value, db)
    if not template:
        logger.warning("No template for achievement")
        return

    template_vars = {
        "badge_name": badge_name,
        "description": description,
    }

    in_app_title = _format_template(template.in_app_title, template_vars)
    in_app_body = _format_template(template.in_app_body, template_vars)
    push_title = _format_template(template.push_title, template_vars)
    push_body = _format_template(template.push_body, template_vars)

    await store_notification(
        user_id=user_id,
        notif_type=NotificationTypeEnum.ACHIEVEMENT.value,
        channel="in_app",
        title=in_app_title,
        body=in_app_body,
        db=db,
    )

    await queue_notification_tasks(
        user_id=user_id,
        notif_type=NotificationTypeEnum.ACHIEVEMENT.value,
        channel="push",
        title=push_title,
        body=push_body,
        template_vars=template_vars,
    )

    logger.info(f"✓ Achievement notification sent to user {user_id} for '{badge_name}'")


async def send_in_app_notification(
    user_id: int,
    notif_type: str,
    title: str,
    body: str,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Send an in-app only notification."""
    if not await should_send_notification(user_id, notif_type, "in_app", db):
        logger.debug(f"In-app notification skipped for user {user_id}")
        return False

    notif = await store_notification(
        user_id=user_id,
        notif_type=notif_type,
        channel="in_app",
        title=title,
        body=body,
        db=db,
    )

    return notif is not None


async def clear_user_preferences_cache(user_id: int) -> bool:
    """Clear cached preferences for a user (when prefs are updated)."""
    from app.core.redis_client import cache_delete

    key = PREF_CACHE_KEY.format(user_id=user_id)
    return cache_delete(key)
