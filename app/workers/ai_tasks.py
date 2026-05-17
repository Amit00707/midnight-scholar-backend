"""
AI Background Tasks — Non-blocking Summary/Quiz Generation
=============================================================
Offloads heavy LLM calls to Celery workers so API stays fast.
Uses retry logic with exponential backoff.
"""

import logging
from celery import shared_task
from app.workers.celery_app import celery_app
from app.core.redis_client import cache_set, cache_get

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="generate_summary_task",
    max_retries=3,
    default_retry_delay=60,
)
def generate_summary_task(self, book_id: int, page_number: int, page_text: str):
    """Background: Generate AI summary for a page with retry logic."""
    try:
        from app.services.ai_engine import generate_summary
        from app.database.session import AsyncSessionLocal
        from app.database.models.book import BookSummary
        import asyncio

        async def _generate():
            # Generate summary via AI engine
            summary = await generate_summary(page_text)

            # Cache the result for quick retrieval
            cache_key = f"summary:book:{book_id}:page:{page_number}"
            cache_set(cache_key, {"summary": summary}, ttl=86400)  # 24h TTL

            logger.info(f"✓ Summary generated for Book {book_id}, Page {page_number}")
            return {"status": "completed", "book_id": book_id, "page": page_number, "summary": summary}

        return asyncio.run(_generate())

    except Exception as exc:
        logger.error(f"Error generating summary for Book {book_id}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    name="generate_quiz_task",
    max_retries=3,
    default_retry_delay=60,
)
def generate_quiz_task(self, book_id: int, page_text: str, num_questions: int = 5):
    """Background: Generate quiz questions from page content with retry logic."""
    try:
        from app.services.ai_engine import generate_quiz
        from app.core.redis_client import cache_set
        import asyncio

        async def _generate():
            # Generate quiz via AI engine
            quiz = await generate_quiz(page_text, num_questions)

            # Cache the result
            cache_key = f"quiz:book:{book_id}"
            cache_set(cache_key, {"quiz": quiz}, ttl=604800)  # 7 days

            logger.info(f"✓ Quiz generated for Book {book_id} ({num_questions} questions)")
            return {"status": "completed", "book_id": book_id, "questions_count": num_questions, "quiz": quiz}

        return asyncio.run(_generate())

    except Exception as exc:
        logger.error(f"Error generating quiz for Book {book_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    name="ingest_book_task",
    max_retries=2,
    default_retry_delay=120,
)
def ingest_book_task(self, book_id: int, pdf_path: str):
    """Background: Parse entire PDF and store page embeddings in Qdrant."""
    try:
        from app.services.pdf_parser import extract_text_from_pdf
        from app.services.vector_store import store_embeddings
        import asyncio

        async def _ingest():
            logger.info(f"[INGESTING] Book {book_id} from {pdf_path}")

            # Extract text from PDF
            pages = await extract_text_from_pdf(pdf_path)
            logger.info(f"  Extracted {len(pages)} pages from PDF")

            # Store embeddings in Qdrant for semantic search
            stored_count = await store_embeddings(book_id, pages)
            logger.info(f"  Stored {stored_count} page embeddings in Qdrant")

            # Cache book ingestion status
            cache_key = f"ingest_status:book:{book_id}"
            cache_set(cache_key, {
                "status": "completed",
                "pages_count": len(pages),
                "embeddings_stored": stored_count
            }, ttl=604800)  # 7 days

            logger.info(f"✓ Book {book_id} ingestion complete")
            return {
                "status": "completed",
                "book_id": book_id,
                "pages_extracted": len(pages),
                "embeddings_stored": stored_count
            }

        return asyncio.run(_ingest())

    except Exception as exc:
        logger.error(f"Error ingesting Book {book_id}: {exc}")
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))
