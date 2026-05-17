"""
Book Models — Book, Chapter, Tag
==================================
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Table
from sqlalchemy.sql import func

from app.database.session import Base

# Many-to-Many: Books <-> Tags
book_tags = Table(
    "book_tags", Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cover_url = Column(String(500), nullable=True)
    pdf_s3_key = Column(String(500), nullable=False)
    total_pages = Column(Integer, default=0)
    difficulty = Column(String(50), default="beginner")
    category = Column(String(100), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)


class BookVersion(Base):
    """Version history for books - allows admin to track and restore previous versions."""
    __tablename__ = "book_versions"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    version_num = Column(Integer, nullable=False)
    title = Column(String(500), nullable=True)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    cover_url = Column(String(500), nullable=True)
    pdf_s3_key = Column(String(500), nullable=True)
    change_note = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Admin audit trail - logs all admin actions."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(255), nullable=True)
    meta_data = Column(Text, nullable=True)  # 'metadata' is reserved in SQLAlchemy
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
