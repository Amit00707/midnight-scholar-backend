"""
Recommendation Engine — Personalized Book Suggestions
========================================================
Analyzes user behavior (reads, interests, highlights) to recommend books.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database.models.progress import ReadingProgress
from app.database.models.book import Book


async def get_recommendations(db: AsyncSession, user_id: int, limit: int = 10) -> List[dict]:
    """Generate personalized book recommendations based on reading history."""
    # Get categories the user has read
    result = await db.execute(
        select(Book.category)
        .join(ReadingProgress, ReadingProgress.book_id == Book.id)
        .where(ReadingProgress.user_id == user_id)
        .group_by(Book.category)
    )
    preferred_categories = [row[0] for row in result.all() if row[0]]

    if not preferred_categories:
        # Cold start: return popular books
        result = await db.execute(select(Book).limit(limit))
        books = result.scalars().all()
        return [{"id": b.id, "title": b.title, "author": b.author, "reason": "Popular"} for b in books]

    # Recommend books from preferred categories user hasn't read
    read_result = await db.execute(
        select(ReadingProgress.book_id).where(ReadingProgress.user_id == user_id)
    )
    read_ids = [r[0] for r in read_result.all()]

    query = select(Book).where(Book.category.in_(preferred_categories))
    if read_ids:
        query = query.where(Book.id.notin_(read_ids))
    query = query.limit(limit)

    result = await db.execute(query)
    books = result.scalars().all()

    return [{"id": b.id, "title": b.title, "author": b.author, "reason": f"Based on your interest in {b.category}"} for b in books]
