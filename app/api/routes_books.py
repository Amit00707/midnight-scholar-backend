# ============================================================
# app/api/routes_books.py
# Midnight Scholar — All Book API Endpoints
# Powered by Open Library (Free, No Key Required)
# ============================================================

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
import httpx
import asyncio
import logging
from app.services.book_service import (
    unified_search,
    unified_books_by_category,
    unified_get_book_detail,
)
from app.services.open_library_service import (
    search_by_author,
    get_trending_books,
    get_recommended_books,
)
from app.core.dependencies import get_current_user  # JWT auth dependency
from app.database.models.user import User
from app.schemas.book import RecommendationRequest, BookDetailResponse

router = APIRouter(prefix="/books", tags=["Books"])
logger = logging.getLogger(__name__)


# ============================================================
# 1. SEARCH BOOKS
# Frontend: Smart Search page, Navbar search bar
# ============================================================
@router.get("/search")
async def search(
    q:     str = Query(..., min_length=1, description="Search title or author"),
    limit: int = Query(10, ge=1, le=40),
    page:  int = Query(1, ge=1),
    lang:  str = Query("eng", description="Language filter"),
):
    """
    GET /api/books/search?q=atomic+habits&limit=10&page=1

    Returns paginated book search results from multiple sources (OL, IA, arXiv).
    """
    try:
        result = await unified_search(query=q, limit=limit, page=page)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search error: {str(e)}")


# ============================================================
# 2. BOOKS BY CATEGORY
# Frontend: Dashboard rows, Book listing filter
# ============================================================
@router.get("/category/{category}")
async def books_by_category(
    category: str,
    limit:    int = Query(12, ge=1, le=40),
    sort:     str = Query("rating", description="rating | new | editions"),
):
    """
    GET /api/books/category/science?limit=12

    Returns books filtered by category using the best available API for that category.
    """
    try:
        result = await unified_books_by_category(
            category=category,
            limit=limit,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Category fetch error: {str(e)}")



# ============================================================
# 3. TRENDING BOOKS
# Frontend: Dashboard Popular Books row, Landing page hero
# ============================================================
@router.get("/trending")
async def trending(
    limit: int = Query(12, ge=1, le=40),
):
    """
    GET /api/books/trending?limit=12

    Returns currently trending books.
    Used by: Dashboard Popular Books row, Landing page.
    """
    try:
        result = await get_trending_books(limit=limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open Library error: {str(e)}")


# ============================================================
# 4. BOOKS BY AUTHOR
# Frontend: Author Profile page
# ============================================================
@router.get("/by-author")
async def books_by_author(
    name:  str = Query(..., min_length=1, description="Author name"),
    limit: int = Query(12, ge=1, le=40),
):
    """
    GET /api/books/by-author?name=James+Clear&limit=12

    Returns all books by a specific author.
    Used by: Author Profile page.
    """
    try:
        result = await search_by_author(author_name=name, limit=limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open Library error: {str(e)}")


# ============================================================
# 5. PERSONALIZED RECOMMENDATIONS
# Frontend: Onboarding Step 3, Dashboard AI Recommended row
# Requires: JWT auth (user must be logged in)
# ============================================================
@router.post("/recommendations")
async def personalized_recommendations(
    body:         RecommendationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    POST /api/books/recommendations
    Body: { "interests": ["science", "technology", "philosophy"] }

    Returns AI-recommended books based on user interests.
    Used by: Onboarding Step 3, Dashboard AI Recommended row.
    Requires: Valid JWT token in Authorization header.
    """
    try:
        result = await get_recommended_books(
            interests=body.interests,
            limit=body.limit_per_category * len(body.interests)
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open Library error: {str(e)}")


# ============================================================
# 5.5 USER LIBRARY
# Frontend: Library page
# Requires: JWT auth
# ============================================================
from app.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models.progress import ReadingProgress

@router.get("/library")
async def get_library(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /api/books/library

    Returns books the user is currently reading or has saved.
    Fetches ReadingProgress from DB and merges with Open Library data.
    """
    try:
        # 1. Get user's progress
        result = await db.execute(
            select(ReadingProgress).where(ReadingProgress.user_id == current_user.id)
        )
        progress_records = result.scalars().all()
        
        if not progress_records:
            return []

        # 2. Fetch all details in parallel
        async def fetch_item(p):
            try:
                detail = await unified_get_book_detail(p.book_id)
                return {
                    "id": p.book_id,
                    "title": detail.get("title", "Unknown Title"),
                    "author": detail.get("author", "Unknown Author"),
                    "cover_url": detail.get("cover_url"),
                    "progress": {
                        "current_page": p.current_page,
                        "total_pages": p.total_pages,
                        "percentage": p.percentage
                    }
                }
            except Exception as e:
                logger.error(f"Failed to fetch library detail for {p.book_id}: {e}")
                return {
                    "id": p.book_id,
                    "title": "Unknown Book",
                    "author": "Unknown Author",
                    "progress": {
                        "current_page": p.current_page,
                        "total_pages": p.total_pages,
                        "percentage": p.percentage
                    }
                }

        tasks = [fetch_item(p) for p in progress_records]
        books = await asyncio.gather(*tasks)
        
        return books
    except Exception as e:
        logger.exception("Error in get_library")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================================
# 7. CLASSIC BOOKS (Real PDFs)
# Frontend: Free books section / Dashboard
# ============================================================
from app.services.open_library_service import get_classic_books

@router.get("/classics")
async def classics(
    search: str = Query("", description="Search term for classic books"),
    limit:  int = Query(12, ge=1, le=40),
):
    """
    GET /api/books/classics
    Returns classic books with FREE downloadable PDFs.
    """
    try:
        result = await get_classic_books(search=search, limit=limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gutenberg error: {str(e)}")


# ============================================================
# 8. SINGLE BOOK DETAIL
# Frontend: Book Details page
# NOTE: Must come AFTER all /books/... named routes
# ============================================================
from app.services.search_service import search_in_book

@router.get("/{book_id}/search")
async def search_inside_book(
    book_id: str,
    q: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user),
):
    """
    Search for text inside a specific book's PDF.
    Returns page-level matches with snippets.
    """
    try:
        book = await unified_get_book_detail(book_id)
        pdf_url = book.get("pdf_url")
        if not pdf_url:
             return {"results": [], "message": "Search unavailable: No PDF found for this book."}

        # For Sprint 1, we pass the URL. fitz.open might need a local file, 
        # so we'll ensure search_in_book handles downloading.
        results = await search_in_book(pdf_url, q)
        return {"results": results, "query": q, "book_id": book_id}
    except Exception as e:
        logger.exception(f"In-book search failed for {book_id}")
        raise HTTPException(status_code=500, detail="In-book search failed")


@router.get("/{ol_id}", response_model=BookDetailResponse)
async def book_detail(ol_id: str):
    """
    GET /api/books/OL82563W

    Returns full details of a single book.
    ol_id = Open Library Work ID (e.g. OL82563W)
    Used by: Book Details page.
    """
    try:
        result = await unified_get_book_detail(book_id=ol_id)
        return result
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=404, detail="Book not found")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Book fetch error: {str(e)}")
