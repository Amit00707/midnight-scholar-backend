"""
Gamification Engine — Points, Badges, Streak Logic
=====================================================
Core business logic for awarding points & checking badge eligibility.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.database.models.gamification import Points, Badge, UserBadge, Streak


async def award_points(db: AsyncSession, user_id: int, amount: int, reason: str):
    """Award wisdom points to a user."""
    points = Points(user_id=user_id, amount=amount, reason=reason)
    db.add(points)


async def check_and_award_badges(db: AsyncSession, user_id: int):
    """Check if the user qualifies for any new badges."""
    total_result = await db.execute(select(func.sum(Points.amount)).where(Points.user_id == user_id))
    total_points = total_result.scalar() or 0

    badges = await db.execute(select(Badge))
    all_badges = badges.scalars().all()

    for badge in all_badges:
        # Check if user already has this badge
        existing = await db.execute(
            select(UserBadge).where(UserBadge.user_id == user_id, UserBadge.badge_id == badge.id)
        )
        if existing.scalar_one_or_none():
            continue

        if badge.requirement_type == "total_points" and total_points >= badge.requirement_value:
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))


async def update_streak(db: AsyncSession, user_id: int):
    """Update the user's reading streak based on today's activity."""
    result = await db.execute(select(Streak).where(Streak.user_id == user_id))
    streak = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not streak:
        streak = Streak(user_id=user_id, current_streak=1, longest_streak=1, last_activity_date=now)
        db.add(streak)
        return

    if streak.last_activity_date:
        days_diff = (now.date() - streak.last_activity_date.date()).days
        if days_diff == 1:
            streak.current_streak += 1
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        elif days_diff > 1:
            streak.current_streak = 1

    streak.last_activity_date = now
