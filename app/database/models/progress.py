"""
Progress Models — Progress, Bookmark, Highlight, Note
=======================================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.sql import func

from app.database.session import Base


class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(String(100), nullable=False, index=True)
    current_page = Column(Integer, default=1)
    total_pages = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    time_spent_minutes = Column(Integer, default=0)
    last_read_at = Column(DateTime(timezone=True), server_default=func.now())


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(String(100), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    label = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(String(100), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    color = Column(String(20), default="amber")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(String(100), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ReadingGaps(Base):
    """Track skipped pages and weak topics for personalized learning insights."""
    __tablename__ = "reading_gaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(String(100), nullable=False, index=True)
    skipped_pages = Column(Text, nullable=True)  # JSON array stored as text
    weak_topics = Column(Text, nullable=True)    # JSON array of detected topics
    gap_score = Column(Float, default=0.0)       # 0-100, higher = more gaps
    detected_at = Column(DateTime(timezone=True), server_default=func.now())


class RevisionItem(Base):
    """Smart revision items generated from weak topics, quiz scores, and bookmarks."""
    __tablename__ = "revision_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(String(100), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    page_refs = Column(Text, nullable=True)      # JSON array of page numbers
    priority = Column(Integer, default=1)        # 1=low, 2=medium, 3=high
    last_revised = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
