"""
Flashcard Models — Flashcard, ReviewLog
=========================================
Persistent flashcard storage with SM-2 spaced repetition fields.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey,
)
from sqlalchemy.sql import func

from app.database.session import Base


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(String(255), nullable=False, index=True)
    source_page = Column(Integer, nullable=True)

    # Content
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    tags = Column(String(500), nullable=True)
    source = Column(String(20), default="ai")  # "ai" | "manual"

    # SM-2 Spaced Repetition Fields
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=0)          # Days until next review
    repetitions = Column(Integer, default=0)       # Consecutive correct answers
    next_review = Column(DateTime(timezone=True), server_default=func.now())
    last_reviewed = Column(DateTime(timezone=True), nullable=True)

    # State
    is_suspended = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)        # 0=Again, 1=Hard, 2=Good, 3=Easy
    time_spent_ms = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Snapshot of SM-2 state after this review
    ease_factor_after = Column(Float)
    interval_after = Column(Integer)
