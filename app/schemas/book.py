"""
Book Schemas — Request/Response Models
========================================
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    total_pages: int
    difficulty: str
    category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookUploadRequest(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    difficulty: str = "beginner"
    category: Optional[str] = None


class BookSearchResult(BaseModel):
    books: List[BookResponse]
    total: int
    page: int
    per_page: int
