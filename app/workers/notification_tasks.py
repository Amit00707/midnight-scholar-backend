"""
Notification Background Tasks — Periodic Streak & Reminder Checks
====================================================================
Runs on a schedule via Celery Beat to check streaks and send reminders.
"""

from app.workers.celery_app import celery_app


@celery_app.task(name="check_streaks_task")
def check_streaks_task():
    """Periodic: Check all user streaks and reset broken ones."""
    print("[CELERY] Checking all user streaks...")
    # TODO: Query all Streak records, compare last_activity_date with today
    return {"status": "completed"}


@celery_app.task(name="send_daily_reminders_task")
def send_daily_reminders_task():
    """Periodic: Send reading reminders to users who haven't read today."""
    print("[CELERY] Sending daily reading reminders...")
    # TODO: Query users without today's ReadingProgress, send email/push
    return {"status": "completed"}
