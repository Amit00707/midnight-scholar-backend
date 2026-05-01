"""
AI Schemas — Request/Response Models
======================================
"""

from pydantic import BaseModel
from typing import List, Optional


class AskRequest(BaseModel):
    book_id: int
    page_number: int
    question: str


class SummaryRequest(BaseModel):
    book_id: int
    page_number: int


class SummaryResponse(BaseModel):
    summary: str
    key_points: List[str]
    page_number: int


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int


class QuizResponse(BaseModel):
    book_id: int
    questions: List[QuizQuestion]


class FlashcardItem(BaseModel):
    front: str
    back: str


class FlashcardResponse(BaseModel):
    book_id: int
    flashcards: List[FlashcardItem]


class DoubtResponse(BaseModel):
    answer: str
    source_page: int
    confidence: float
