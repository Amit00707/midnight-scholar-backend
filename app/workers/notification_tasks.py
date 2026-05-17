"""
Notification Background Tasks — Periodic Streak & Reminder Checks
====================================================================
Runs on a schedule via Celery Beat to check streaks and send reminders.
Uses database queries and notification service integration.
"""

import logging
from datetime import datetime, timedelta
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="check_streaks_task",
    max_retries=2,
)
def check_streaks_task(self):
    """Periodic: Check all user streaks and reset broken ones (runs hourly)."""
    try:
        from app.database.session import AsyncSessionLocal
        from app.database.models.gamification import Streak
        from sqlalchemy import select, func
        import asyncio

        async def _check_streaks():
            async with AsyncSessionLocal() as db:
                # Get all active streaks
                query = select(Streak).where(Streak.current > 0)
                result = await db.execute(query)
                streaks = result.scalars().all()

                reset_count = 0
                for streak in streaks:
                    # If no activity today, reset the streak
                    today = datetime.utcnow().date()
                    if streak.last_activity_date < today:
                        streak.current = 0
                        reset_count += 1
                        logger.info(f"Reset streak for user {streak.user_id}")

                if reset_count > 0:
                    await db.commit()

                logger.info(f"✓ Checked {len(streaks)} streaks, reset {reset_count}")
                return {"status": "completed", "checked": len(streaks), "reset": reset_count}

        return asyncio.run(_check_streaks())

    except Exception as exc:
        logger.error(f"Error checking streaks: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(
    bind=True,
    name="send_daily_reminders_task",
    max_retries=2,
)
def send_daily_reminders_task(self):
    """Periodic: Send reading reminders to users who haven't read today (runs at 9 AM)."""
    try:
        from app.database.session import AsyncSessionLocal
        from app.database.models.user import User
        from app.database.models.progress import ReadingProgress
        from app.services.notification_service import send_streak_reminder
        from sqlalchemy import select, func
        from datetime import datetime
        import asyncio

        async def _send_reminders():
            async with AsyncSessionLocal() as db:
                today = datetime.utcnow().date()

                # Find users who haven't read today
                # Subquery: users with today's reading progress
                today_progress = select(ReadingProgress.user_id).where(
                    func.date(ReadingProgress.created_at) == today
                )

                # Select users NOT in today's progress (excluding those who already read)
                query = select(User).where(
                    ~User.id.in_(select(ReadingProgress.user_id).where(
                        func.date(ReadingProgress.created_at) == today
                    ))
                )
                result = await db.execute(query)
                users_to_remind = result.scalars().all()

                reminder_count = 0
                for user in users_to_remind:
                    try:
                        # Send reminder notification
                        await send_streak_reminder(user.id)
                        reminder_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to send reminder to user {user.id}: {e}")

                logger.info(f"✓ Sent {reminder_count} daily reading reminders")
                return {"status": "completed", "reminders_sent": reminder_count}

        return asyncio.run(_send_reminders())

    except Exception as exc:
        logger.error(f"Error sending daily reminders: {exc}")
        raise self.retry(exc=exc, countdown=600)
