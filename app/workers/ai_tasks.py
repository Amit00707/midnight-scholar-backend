"""
AI Background Tasks — Non-blocking Summary/Quiz Generation
=============================================================
Offloads heavy LLM calls to Celery workers so API stays fast.
"""

from app.workers.celery_app import celery_app


@celery_app.task(name="generate_summary_task")
def generate_summary_task(book_id: int, page_number: int, page_text: str):
    """Background: Generate AI summary for a page."""
    # TODO: Call ai_engine.generate_summary() synchronously
    print(f"[CELERY] Generating summary for Book {book_id}, Page {page_number}")
    return {"status": "completed", "book_id": book_id, "page": page_number}


@celery_app.task(name="generate_quiz_task")
def generate_quiz_task(book_id: int, page_text: str):
    """Background: Generate quiz questions from page content."""
    print(f"[CELERY] Generating quiz for Book {book_id}")
    return {"status": "completed", "book_id": book_id}


@celery_app.task(name="ingest_book_task")
def ingest_book_task(book_id: int, pdf_path: str):
    """Background: Parse entire PDF and store page embeddings in Qdrant."""
    print(f"[CELERY] Ingesting Book {book_id} from {pdf_path}")
    # TODO: Loop through pages, extract text, store embeddings
    return {"status": "completed", "book_id": book_id}
