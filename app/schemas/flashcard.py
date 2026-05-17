"""
Flashcard Schemas — Request/Response Models
=============================================
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


# ─── Generation ──────────────────────────────────────────────
class FlashcardGenerateRequest(BaseModel):
    book_id: str
    page_number: int
    context: Optional[str] = None


# ─── Manual Creation ─────────────────────────────────────────
class FlashcardCreateRequest(BaseModel):
    book_id: str
    source_page: Optional[int] = None
    front: str = Field(..., min_length=1, max_length=2000)
    back: str = Field(..., min_length=1, max_length=5000)
    tags: Optional[str] = None


# ─── Update ──────────────────────────────────────────────────
class FlashcardUpdateRequest(BaseModel):
    front: Optional[str] = Field(None, min_length=1, max_length=2000)
    back: Optional[str] = Field(None, min_length=1, max_length=5000)
    tags: Optional[str] = None
    is_suspended: Optional[bool] = None


# ─── Review ──────────────────────────────────────────────────
class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=0, le=3)  # 0=Again, 1=Hard, 2=Good, 3=Easy
    time_spent_ms: Optional[int] = None


# ─── Response Models ─────────────────────────────────────────
class FlashcardOut(BaseModel):
    id: int
    front: str
    back: str
    book_id: str
    source_page: Optional[int]
    source: str
    tags: Optional[str]
    ease_factor: float
    interval: int
    repetitions: int
    next_review: datetime
    last_reviewed: Optional[datetime]
    is_suspended: bool
    created_at: datetime
    interval_previews: Optional[Dict[int, str]] = None  # rating → "1d", "4d", etc.

    class Config:
        from_attributes = True


class FlashcardListResponse(BaseModel):
    flashcards: List[FlashcardOut]
    total: int


class ReviewResponse(BaseModel):
    flashcard_id: int
    new_interval: int
    new_ease_factor: float
    next_review: datetime
    points_earned: int


class FlashcardStats(BaseModel):
    total_cards: int
    due_today: int
    cards_reviewed_today: int
    average_ease: float
    mature_cards: int       # interval > 21 days
    young_cards: int        # interval <= 21 days
    new_cards: int          # repetitions == 0
    suspended_cards: int
    retention_rate: float   # % of Good/Easy in last 30 days
    books: List[Dict]       # [{book_id, card_count, due_count}]


class GenerateResponse(BaseModel):
    book_id: str
    page_number: int
    flashcards: List[FlashcardOut]
    new_count: int          # How many were newly created
    duplicate_count: int    # How many were skipped as duplicates
