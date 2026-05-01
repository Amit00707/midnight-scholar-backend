"""
Reader Routes — /progress /bookmarks /highlights /notes
=========================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.database.models.progress import ReadingProgress, Bookmark, Highlight, Note
from app.core.dependencies import get_current_user
from app.database.models.user import User
from app.schemas.reader import ProgressUpdate, ProgressResponse, BookmarkCreate, HighlightCreate, NoteCreate

router = APIRouter()


@router.post("/progress", response_model=ProgressResponse)
async def update_progress(payload: ProgressUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update reading progress for a book."""
    result = await db.execute(
        select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.book_id == payload.book_id)
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.current_page = payload.current_page
        progress.time_spent_minutes += payload.time_spent_minutes
        progress.percentage = (payload.current_page / progress.total_pages * 100) if progress.total_pages else 0
    else:
        progress = ReadingProgress(
            user_id=user.id,
            book_id=payload.book_id,
            current_page=payload.current_page,
            time_spent_minutes=payload.time_spent_minutes,
        )
        db.add(progress)

    await db.flush()
    return progress


@router.post("/bookmarks")
async def create_bookmark(payload: BookmarkCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a bookmark on a specific page."""
    bookmark = Bookmark(user_id=user.id, book_id=payload.book_id, page_number=payload.page_number, label=payload.label)
    db.add(bookmark)
    return {"message": "Bookmark created"}


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
    return {"message": "Note created"}
