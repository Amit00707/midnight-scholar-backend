"""
Reader Routes — /progress /bookmarks /highlights /notes
=========================================================
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.database.models.progress import ReadingProgress, Bookmark, Highlight, Note
from app.core.dependencies import get_current_user
from app.database.models.user import User
from app.schemas.reader import ProgressUpdate, ProgressResponse, BookmarkCreate, HighlightCreate, NoteCreate
from app.services.gamification_engine import update_streak, update_daily_goal

router = APIRouter(prefix="/reader", tags=["Reader"])


@router.get("/progress", response_model=list[ProgressResponse])
async def get_all_progress(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all reading progress for a user."""
    result = await db.execute(select(ReadingProgress).where(ReadingProgress.user_id == user.id))
    return result.scalars().all()

@router.get("/progress/{book_id}", response_model=Optional[ProgressResponse])
async def get_book_progress(book_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get reading progress for a specific book."""
    result = await db.execute(
        select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.book_id == book_id)
    )
    return result.scalar_one_or_none()

@router.api_route("/progress", methods=["POST", "PATCH"], response_model=ProgressResponse)
async def update_progress(payload: ProgressUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update reading progress for a book."""

    result = await db.execute(
        select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.book_id == payload.book_id)
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.current_page = payload.current_page
        # Fix: Handle None values properly
        progress.time_spent_minutes = (progress.time_spent_minutes or 0) + payload.time_spent_minutes
        progress.percentage = (payload.current_page / (progress.total_pages or 1) * 100) if progress.total_pages else 0
    else:
        progress = ReadingProgress(
            user_id=user.id,
            book_id=payload.book_id,
            current_page=payload.current_page,
            time_spent_minutes=payload.time_spent_minutes or 0,
            total_pages=0,
        )
        db.add(progress)

    await db.flush()
    await update_streak(db, user.id)
    await update_daily_goal(db, user.id, "pages", 1)
    await update_daily_goal(db, user.id, "minutes", payload.time_spent_minutes or 0)
    await db.commit()
    return progress


@router.post("/bookmarks")
async def create_bookmark(payload: BookmarkCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a bookmark on a specific page."""
    bookmark = Bookmark(user_id=user.id, book_id=payload.book_id, page_number=payload.page_number, label=payload.label)
    db.add(bookmark)
    await db.commit()
    return {"message": "Bookmark created"}


@router.get("/bookmarks/{book_id}")
async def get_bookmarks(book_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all bookmarks for a specific book."""
    from sqlalchemy import desc
    result = await db.execute(
        select(Bookmark)
        .where(Bookmark.user_id == user.id, Bookmark.book_id == book_id)
        .order_by(desc(Bookmark.created_at))
    )
    bookmarks = result.scalars().all()
    return {"bookmarks": bookmarks}


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a bookmark."""
    result = await db.execute(select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user.id))
    bookmark = result.scalar_one_or_none()
    if bookmark:
        await db.delete(bookmark)
        await db.commit()
    return {"message": "Bookmark deleted"}


@router.post("/highlights")
async def create_highlight(payload: HighlightCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a text highlight on a specific page."""
    highlight = Highlight(user_id=user.id, book_id=payload.book_id, page_number=payload.page_number, text_content=payload.text_content, color=payload.color)
    db.add(highlight)
    return {"message": "Highlight created"}


@router.post("/notes")
async def create_note(payload: NoteCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a note on a specific page."""
    note = Note(user_id=user.id, book_id=payload.book_id, page_number=payload.page_number, content=payload.content)
    db.add(note)
    await db.commit()
    return {"message": "Note created"}


@router.get("/notes/{book_id}")
async def get_notes(book_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all notes for a specific book."""
    from sqlalchemy import desc
    result = await db.execute(
        select(Note)
        .where(Note.user_id == user.id, Note.book_id == book_id)
        .order_by(desc(Note.created_at))
    )
    notes = result.scalars().all()
    return {"notes": notes}


@router.delete("/notes/{note_id}")
async def delete_note(note_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a note."""
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    note = result.scalar_one_or_none()
    if note:
        await db.delete(note)
        await db.commit()
    return {"message": "Note deleted"}


# ============================================================
# READING GAPS / WEAK TOPIC DETECTION
# ============================================================
import json
from datetime import datetime

@router.get("/gaps/{book_id}")
async def get_reading_gaps(book_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get reading gaps and weak topics for a specific book."""
    from app.database.models.progress import ReadingGaps
    result = await db.execute(
        select(ReadingGaps).where(ReadingGaps.user_id == user.id, ReadingGaps.book_id == book_id)
    )
    gap = result.scalar_one_or_none()
    if not gap:
        return {"skipped_pages": [], "weak_topics": [], "gap_score": 0}
    return {
        "skipped_pages": json.loads(gap.skipped_pages) if gap.skipped_pages else [],
        "weak_topics": json.loads(gap.weak_topics) if gap.weak_topics else [],
        "gap_score": gap.gap_score,
        "detected_at": gap.detected_at.isoformat() if gap.detected_at else None
    }


@router.post("/gaps/{book_id}/detect")
async def detect_reading_gaps(book_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Detect skipped pages and weak topics based on reading progress."""
    from app.database.models.progress import ReadingGaps, ReadingProgress

    # Get user's progress for this book
    result = await db.execute(
        select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.book_id == book_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        return {"message": "No reading progress found for this book"}

    # Simple gap detection: if user skipped ahead more than 5 pages at once
    # In production, this would use AI to analyze content
    skipped_pages = []
    current_page = progress.current_page
    total_pages = progress.total_pages

    # Calculate gap score based on how much of the book was read vs skipped
    if total_pages > 0:
        reading_percentage = (current_page / total_pages) * 100
        gap_score = max(0, 100 - reading_percentage)
    else:
        gap_score = 0

    # Detect weak topics (placeholder - would use AI in production)
    weak_topics = ["Mathematics", "Physics", "Chemistry"]  # Placeholder

    # Save or update gaps
    result = await db.execute(
        select(ReadingGaps).where(ReadingGaps.user_id == user.id, ReadingGaps.book_id == book_id)
    )
    gap = result.scalar_one_or_none()

    if gap:
        gap.skipped_pages = json.dumps(skipped_pages)
        gap.weak_topics = json.dumps(weak_topics)
        gap.gap_score = gap_score
        gap.detected_at = datetime.utcnow()
    else:
        gap = ReadingGaps(
            user_id=user.id,
            book_id=book_id,
            skipped_pages=json.dumps(skipped_pages),
            weak_topics=json.dumps(weak_topics),
            gap_score=gap_score
        )
        db.add(gap)

    await db.commit()
    return {
        "message": "Gaps detected successfully",
        "skipped_pages": skipped_pages,
        "weak_topics": weak_topics,
        "gap_score": gap_score
    }


# ============================================================
# SMART REVISION LISTS
# ============================================================
@router.get("/revision")
async def get_revision_items(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get smart revision items for the user."""
    from app.database.models.progress import RevisionItem
    from sqlalchemy import desc
    result = await db.execute(
        select(RevisionItem)
        .where(RevisionItem.user_id == user.id)
        .order_by(desc(RevisionItem.priority), RevisionItem.due_date)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": item.id,
                "book_id": item.book_id,
                "topic": item.topic,
                "page_refs": json.loads(item.page_refs) if item.page_refs else [],
                "priority": item.priority,
                "due_date": item.due_date.isoformat() if item.due_date else None,
                "last_revised": item.last_revised.isoformat() if item.last_revised else None
            }
            for item in items
        ]
    }


@router.post("/revision/{item_id}/done")
async def mark_revision_done(item_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Mark a revision item as done and compute next due date (spaced repetition)."""
    from app.database.models.progress import RevisionItem
    result = await db.execute(
        select(RevisionItem).where(RevisionItem.id == item_id, RevisionItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()

    if not item:
        return {"error": "Revision item not found"}, 404

    now = datetime.utcnow()
    item.last_revised = now

    # Simple spaced repetition: next due in 1 day (would use SM-2 in production)
    from datetime import timedelta
    item.due_date = now + timedelta(days=1)

    # Lower priority after completion
    item.priority = max(1, item.priority - 1)

    await db.commit()
    return {"message": "Revision marked as done", "due_date": item.due_date.isoformat()}
