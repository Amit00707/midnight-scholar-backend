"""
Book Routes — /books /books/{id} /search
==========================================
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database.session import get_db
from app.database.models.book import Book
from app.core.dependencies import get_current_user
from app.database.models.user import User
from app.schemas.book import BookResponse, BookUploadRequest, BookSearchResult

router = APIRouter()


@router.get("/books", response_model=BookSearchResult)
async def list_books(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all books with optional filters and pagination."""
    query = select(Book)
    if category:
        query = query.where(Book.category == category)
    if difficulty:
        query = query.where(Book.difficulty == difficulty)
    if q:
        query = query.where(Book.title.ilike(f"%{q}%"))

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    books = result.scalars().all()

    return BookSearchResult(books=books, total=len(books), page=page, per_page=per_page)


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single book by its ID."""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books", response_model=BookResponse)
async def upload_book(
    metadata: BookUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new book (PDF upload handled separately via S3)."""
    book = Book(
        title=metadata.title,
        author=metadata.author,
        description=metadata.description,
        difficulty=metadata.difficulty,
        category=metadata.category,
        pdf_s3_key="pending",
        uploaded_by=user.id,
    )
    db.add(book)
    await db.flush()
    return book
