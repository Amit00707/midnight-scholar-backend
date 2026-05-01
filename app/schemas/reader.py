"""
Reader Schemas — Request/Response Models
==========================================
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProgressUpdate(BaseModel):
    book_id: int
    current_page: int
    time_spent_minutes: int = 0


class ProgressResponse(BaseModel):
    book_id: int
    current_page: int
    total_pages: int
    percentage: float
    time_spent_minutes: int
    last_read_at: datetime

    class Config:
        from_attributes = True


class BookmarkCreate(BaseModel):
    book_id: int
    page_number: int
    label: Optional[str] = None


class HighlightCreate(BaseModel):
    book_id: int
    page_number: int
    text_content: str
    color: str = "amber"


class NoteCreate(BaseModel):
    book_id: int
    page_number: int
    content: str
