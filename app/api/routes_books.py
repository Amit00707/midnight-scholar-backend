# ============================================================
# app/api/routes_books.py
# Midnight Scholar — All Book API Endpoints
# Powered by Open Library (Free, No Key Required)
# ============================================================

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from app.services.open_library_service import (
    search_books,
    search_by_author,
    get_books_by_category,
    get_book_detail,
    get_trending_books,
    get_recommended_books,
)
from app.core.dependencies import get_current_user  # JWT auth dependency
from app.schemas.book import RecommendationRequest

router = APIRouter(prefix="/api/books", tags=["Books"])


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

    Returns paginated book search results.
    Used by the Smart Search page and navbar search bar.
    """
    try:
        result = await search_books(query=q, limit=limit, page=page)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open Library error: {str(e)}")


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

    Returns books filtered by category.
    Categories: fiction, science, history, technology,
                business, self-help, philosophy, mathematics,
                psychology, biography, economics, art
    """
    try:
        result = await get_books_by_category(
            category=category,
            limit=limit,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open Library error: {str(e)}")


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
# 6. SINGLE BOOK DETAIL
# Frontend: Book Details page
# NOTE: Must come AFTER all /books/... named routes
# ============================================================
@router.get("/{ol_id}")
async def book_detail(ol_id: str):
    """
    GET /api/books/OL82563W

    Returns full details of a single book.
    ol_id = Open Library Work ID (e.g. OL82563W)
    Used by: Book Details page.
    """
    try:
        result = await get_book_detail(work_id=ol_id)
        return result
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=404, detail="Book not found")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open Library error: {str(e)}")
