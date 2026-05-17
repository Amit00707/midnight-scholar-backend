"""
Seed Notification Templates — Bootstrap Default Templates
============================================================
Creates default notification templates for all notification types on startup.
Used to populate email/push/in-app message templates.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.notification import NotificationTemplate, NotificationTypeEnum
from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


async def seed_templates():
    """
    Create default notification templates if they don't exist.
    Seeds templates for all notification types with professional messaging.
    """
    session_factory = get_session_factory()
    async with session_factory() as db:
        templates = [
            {
                "notification_type": NotificationTypeEnum.STREAK_REMINDER,
                "email_subject": "Keep Your {streak_count}-Day Reading Streak Alive!",
                "email_body": (
                    "Hi {user_name},\n\n"
                    "You've built an amazing {streak_count}-day reading streak! "
                    "Read one more page today to keep it going.\n\n"
                    "Your reading goal is within reach. Let's keep this momentum going!\n\n"
                    "Happy reading! 📚"
                ),
                "push_title": "{streak_count}-Day Streak!",
                "push_body": "Keep it going - read today and maintain your streak!",
                "in_app_title": "Streak Reminder",
                "in_app_body": "Your {streak_count}-day reading streak is waiting... Read one more page today!",
            },
            {
                "notification_type": NotificationTypeEnum.QUIZ_DUE,
                "email_subject": "Quiz Alert: {quiz_name} Due Soon",
                "email_body": (
                    "Hi {user_name},\n\n"
                    "This is a reminder that the quiz '{quiz_name}' is due soon.\n\n"
                    "Make sure to complete it before the deadline. Click the link below to take the quiz.\n\n"
                    "Best of luck! 📝"
                ),
                "push_title": "Quiz Due: {quiz_name}",
                "push_body": "Don't miss the deadline for {quiz_name}!",
                "in_app_title": "Quiz Due",
                "in_app_body": "The quiz '{quiz_name}' is due soon. Make sure to complete it in time!",
            },
            {
                "notification_type": NotificationTypeEnum.ACHIEVEMENT,
                "email_subject": "Achievement Unlocked: {badge_name}!",
                "email_body": (
                    "Congratulations {user_name}!\n\n"
                    "You've unlocked a new achievement: {badge_name}\n\n"
                    "{description}\n\n"
                    "Keep up the great work! 🎉"
                ),
                "push_title": "Achievement: {badge_name}",
                "push_body": "You've earned a new badge! Tap to see details.",
                "in_app_title": "Achievement Unlocked!",
                "in_app_body": "Congratulations! You've earned {badge_name}. {description}",
            },
            {
                "notification_type": NotificationTypeEnum.MESSAGE,
                "email_subject": "New Message from {sender_name}",
                "email_body": (
                    "Hi {user_name},\n\n"
                    "You have a new message from {sender_name}:\n\n"
                    "\"{message_preview}\"\n\n"
                    "Log in to Midnight Scholar to read the full message and reply.\n\n"
                    "Best regards,\n"
                    "Midnight Scholar Team"
                ),
                "push_title": "Message from {sender_name}",
                "push_body": "{message_preview}",
                "in_app_title": "New Message",
                "in_app_body": "{sender_name}: {message_preview}",
            },
            {
                "notification_type": NotificationTypeEnum.READING_REMINDER,
                "email_subject": "Time to Read!",
                "email_body": (
                    "Hi {user_name},\n\n"
                    "It's been a while since your last reading session. "
                    "Why not dive into a book right now?\n\n"
                    "You have {books_available} books waiting for you in your library.\n\n"
                    "Happy reading! 📖"
                ),
                "push_title": "Time to Read!",
                "push_body": "You have {books_available} books waiting. Start reading now!",
                "in_app_title": "Reading Reminder",
                "in_app_body": "It's been a while! Why not read a page or two from one of your books?",
            },
            {
                "notification_type": NotificationTypeEnum.ANNOUNCEMENT,
                "email_subject": "{announcement_title}",
                "email_body": (
                    "Hi {user_name},\n\n"
                    "{announcement_body}\n\n"
                    "Thank you,\n"
                    "Midnight Scholar Team"
                ),
                "push_title": "{announcement_title}",
                "push_body": "{announcement_preview}",
                "in_app_title": "{announcement_title}",
                "in_app_body": "{announcement_body}",
            },
            {
                "notification_type": NotificationTypeEnum.CLASS_ASSIGNMENT,
                "email_subject": "New Assignment: {assignment_name}",
                "email_body": (
                    "Hi {user_name},\n\n"
                    "Your teacher has assigned a new task: {assignment_name}\n\n"
                    "Due date: {due_date}\n\n"
                    "Log in to view the full assignment and submit your work.\n\n"
                    "Good luck! 📚"
                ),
                "push_title": "New Assignment: {assignment_name}",
                "push_body": "Due: {due_date}",
                "in_app_title": "Class Assignment",
                "in_app_body": "New assignment: {assignment_name}. Due: {due_date}",
            },
            {
                "notification_type": NotificationTypeEnum.COMMENT_REPLY,
                "email_subject": "{replier_name} replied to your comment",
                "email_body": (
                    "Hi {user_name},\n\n"
                    "{replier_name} replied to your comment:\n\n"
                    "\"{reply_text}\"\n\n"
                    "Log in to view the full conversation.\n\n"
                    "Best regards,\n"
                    "Midnight Scholar Team"
                ),
                "push_title": "Reply from {replier_name}",
                "push_body": "{reply_text}",
                "in_app_title": "Comment Reply",
                "in_app_body": "{replier_name}: {reply_text}",
            },
        ]

        seeded_count = 0
        skipped_count = 0

        for template_data in templates:
            notif_type = template_data["notification_type"]

            # Check if template already exists
            result = await db.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.notification_type == notif_type
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug(f"Template for {notif_type.value} already exists, skipping")
                skipped_count += 1
                continue

            # Create new template
            template = NotificationTemplate(
                notification_type=notif_type,
                email_subject=template_data["email_subject"],
                email_body=template_data["email_body"],
                push_title=template_data["push_title"],
                push_body=template_data["push_body"],
                in_app_title=template_data["in_app_title"],
                in_app_body=template_data["in_app_body"],
            )
            db.add(template)
            seeded_count += 1

        if seeded_count > 0:
            await db.commit()
            logger.info(f"✓ Seeded {seeded_count} notification templates")

        if skipped_count > 0:
            logger.debug(f"Skipped {skipped_count} existing templates")

        return {
            "status": "completed",
            "seeded": seeded_count,
            "skipped": skipped_count,
        }
