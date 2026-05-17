"""
Analytics Routes — Weak Topics, Reading Trends, Progress Stats
==============================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict

from app.database.session import get_db
from app.database.models.user import User
from app.database.models.flashcard import Flashcard, ReviewLog
from app.database.models.progress import ReadingProgress, Note
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/weak-topics")
async def get_weak_topics(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Identify books/pages where the user is struggling based on flashcard reviews."""

    # Query for low-rating reviews (0=Again, 1=Hard)
    query = (
        select(
            Flashcard.book_id,
            Flashcard.source_page,
            func.count(ReviewLog.id).label("struggle_count")
        )
        .join(ReviewLog, Flashcard.id == ReviewLog.flashcard_id)
        .where(
            and_(
                Flashcard.user_id == user.id,
                ReviewLog.rating <= 1
            )
        )
        .group_by(Flashcard.book_id, Flashcard.source_page)
        .order_by(func.count(ReviewLog.id).desc())
        .limit(10)
    )

    result = await db.execute(query)
    weak_spots = []
    for row in result.fetchall():
        weak_spots.append({
            "book_id": row[0],
            "page_number": row[1],
            "struggle_score": row[2]
        })

    return {"weak_topics": weak_spots}

@router.get("/reading-habits")
async def get_reading_habits(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Analyze time spent and frequency of reading."""
    result = await db.execute(
        select(
            ReadingProgress.book_id,
            ReadingProgress.time_spent_minutes,
            ReadingProgress.current_page,
            ReadingProgress.total_pages
        ).where(ReadingProgress.user_id == user.id)
    )

    data = []
    for row in result.fetchall():
        data.append({
            "book_id": row[0],
            "minutes_spent": row[1],
            "completion_ratio": (row[2] / row[3]) if row[3] > 0 else 0
        })

    return {"habits": data}