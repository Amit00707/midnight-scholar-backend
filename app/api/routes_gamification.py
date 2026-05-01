"""
Gamification Routes — /points /badges /leaderboard /streak
=============================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.session import get_db
from app.database.models.gamification import Points, Badge, UserBadge, Streak
from app.database.models.user import User
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/points")
async def get_my_points(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get total wisdom score for the current user."""
    result = await db.execute(select(func.sum(Points.amount)).where(Points.user_id == user.id))
    total = result.scalar() or 0
    return {"user_id": user.id, "total_points": total}


@router.get("/badges")
async def get_my_badges(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all badges earned by the current user."""
    result = await db.execute(
        select(Badge).join(UserBadge).where(UserBadge.user_id == user.id)
    )
    badges = result.scalars().all()
    return {"badges": [{"name": b.name, "description": b.description} for b in badges]}


@router.get("/leaderboard")
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    """Get the global top 50 scholars by wisdom score."""
    result = await db.execute(
        select(Points.user_id, func.sum(Points.amount).label("total"))
        .group_by(Points.user_id)
        .order_by(func.sum(Points.amount).desc())
        .limit(50)
    )
    rows = result.all()
    return {"leaderboard": [{"user_id": r[0], "score": r[1]} for r in rows]}


@router.get("/streak")
async def get_my_streak(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get current reading streak for the user."""
    result = await db.execute(select(Streak).where(Streak.user_id == user.id))
    streak = result.scalar_one_or_none()
    if not streak:
        return {"current_streak": 0, "longest_streak": 0}
    return {"current_streak": streak.current_streak, "longest_streak": streak.longest_streak}
