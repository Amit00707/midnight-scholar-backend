# ============================================================
# app/schemas/book.py
# Midnight Scholar — Book Pydantic Schemas
# Request validation + Response structure
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional


# ============================================================
# REQUEST SCHEMAS (what frontend sends to backend)
# ============================================================

class RecommendationRequest(BaseModel):
    """
    POST /api/books/recommendations
    Sent by: Onboarding Step 3, Dashboard AI row
    """
    interests:          list[str] = Field(
                            ...,
                            min_length=1,
                            max_length=5,
                            description="User interest categories from onboarding",
                            example=["science", "technology", "philosophy"]
                        )
    limit_per_category: int       = Field(
                            default=4,
                            ge=1,
                            le=10,
                            description="Max books per category"
                        )


# ============================================================
# RESPONSE SCHEMAS (what backend sends to frontend)
# ============================================================

class BookResponse(BaseModel):
    """
    Single book object — returned in all list endpoints
    """
    id:             Optional[str]   = None
    ol_key:         Optional[str]   = None
    title:          str
    author:         str
    authors:        list[str]       = []
    cover_url:      str
    cover_id:       Optional[int]   = None
    isbn:           Optional[str]   = None
    category:       str             = "General"
    subjects:       list[str]       = []
    language:       str             = "eng"
    page_count:     int             = 0
    difficulty:     str             = "Unknown"
    reading_hours:  float           = 0
    published_year: int             = 0
    rating:         float           = 0
    rating_count:   int             = 0
    edition_count:  int             = 1
    has_ebook:      bool            = False
    preview_url:    Optional[str]   = None

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    """
    Paginated list of books
    """
    results:      list[BookResponse]
    total:        int
    page:         int             = 1
    limit:        int             = 10
    query:        Optional[str]   = None
    total_pages:  Optional[int]   = None


class BookDetailResponse(BookResponse):
    """
    Extended book detail — for Book Details page
    """
    description:    str             = ""
    cover_url_md:   Optional[str]   = None
    author_keys:    list[str]       = []
    created:        Optional[str]   = None
    last_modified:  Optional[str]   = None


class CategoryResponse(BaseModel):
    """
    Books by category response
    """
    category: str
    results:  list[BookResponse]
    total:    int


class RecommendationResponse(BaseModel):
    """
    Personalized recommendations response
    """
    results:   list[BookResponse]
    total:     int
    interests: list[str]
