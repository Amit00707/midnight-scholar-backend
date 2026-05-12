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


@router.get("/progress", response_model=list[ProgressResponse])
async def get_all_progress(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all reading progress for a user."""
    result = await db.execute(select(ReadingProgress).where(ReadingProgress.user_id == user.id))
    return result.scalars().all()

@router.api_route("/progress", methods=["POST", "PATCH"], response_model=ProgressResponse)
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
