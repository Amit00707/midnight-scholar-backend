"""
Social Schemas — Request/Response Models
==========================================
"""

from pydantic import BaseModel
from typing import Optional


class CommentCreate(BaseModel):
    book_id: int
    content: str


class NoteCreate(BaseModel):
    book_id: int
    page_number: int
    content: str
    is_public: bool = True


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
