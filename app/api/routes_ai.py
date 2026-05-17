"""
AI Routes — /summary /quiz /flashcards /ask
==============================================
All AI endpoints use the ai_engine service which gracefully
falls back to mock data when OPENAI_API_KEY is not set.
AI responses are cached in Redis for 24 hours to reduce API costs.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_current_user
from app.database.models.book import Book
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.ai import (
    AskRequest,
    DoubtResponse,
    FlashcardResponse,
    LibraryChatRequest,
    LibraryChatResponse,
    QuizResponse,
    SummaryRequest,
    SummaryResponse,
)
from app.services import ai_engine
from app.core.redis_client import cache_get, cache_set

router = APIRouter(prefix="/ai", tags=["AI"])

# Cache TTL: 24 hours (86400 seconds) for AI responses
AI_CACHE_TTL = 86400


@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(
    payload: SummaryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate an AI summary of the current page or book overview."""
    # Check cache first (LAW 4: AI Rate Limiting)
    cache_key = f"ai:summary:{payload.book_id}:{payload.page_number}"
    cached = cache_get(cache_key)
    if cached:
        return SummaryResponse(**cached)

    # 1. Try to find book in database or fetch from service
    from app.services.open_library_service import get_book_detail
    try:
        book_data = await get_book_detail(payload.book_id)
        context = f"Book Title: {book_data.get('title')}\nAuthor: {book_data.get('author')}\nDescription: {book_data.get('description')}\n"
    except Exception:
        context = f"Book ID: {payload.book_id}"

    page_text = f"{context}\nAnalyzing Page {payload.page_number}."

    result = await ai_engine.generate_summary(page_text)

    response_data = {
        "summary": result.get("summary", ""),
        "key_points": result.get("key_points", []),
        "page_number": payload.page_number,
    }

    # Cache the result for 24 hours
    cache_set(cache_key, response_data, AI_CACHE_TTL)

    return SummaryResponse(**response_data)


@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(
    payload: SummaryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered quiz questions from a page or book concepts."""
    # Check cache first (LAW 4: AI Rate Limiting)
    cache_key = f"ai:quiz:{payload.book_id}:{payload.page_number}"
    cached = cache_get(cache_key)
    if cached:
        return QuizResponse(**cached)

    from app.services.open_library_service import get_book_detail
    try:
        book_data = await get_book_detail(payload.book_id)
        context = f"Book Title: {book_data.get('title')}\nDescription: {book_data.get('description')}"
    except Exception:
        context = f"Book ID: {payload.book_id}"

    page_text = f"{context}\nConcepts from Page {payload.page_number}."

    questions = await ai_engine.generate_quiz(page_text)

    response_data = {"book_id": payload.book_id, "questions": questions}

    # Cache the result for 24 hours
    cache_set(cache_key, response_data, AI_CACHE_TTL)

    return QuizResponse(**response_data)


@router.post("/flashcards", response_model=FlashcardResponse)
async def generate_flashcards(
    payload: SummaryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate spaced-repetition flashcards from a page or book knowledge."""
    # Check cache first (LAW 4: AI Rate Limiting)
    cache_key = f"ai:flashcards:{payload.book_id}:{payload.page_number}"
    cached = cache_get(cache_key)
    if cached:
        return FlashcardResponse(**cached)

    from app.services.open_library_service import get_book_detail
    try:
        book_data = await get_book_detail(payload.book_id)
        context = f"Book Title: {book_data.get('title')}\nDescription: {book_data.get('description')}"
    except Exception:
        context = f"Book ID: {payload.book_id}"

    page_text = f"{context}\nKnowledge points from Page {payload.page_number}."

    flashcards = await ai_engine.generate_flashcards(page_text)

    response_data = {"book_id": payload.book_id, "flashcards": flashcards}

    # Cache the result for 24 hours
    cache_set(cache_key, response_data, AI_CACHE_TTL)

    return FlashcardResponse(**response_data)


@router.post("/ask", response_model=DoubtResponse)
async def ask_doubt(
    payload: AskRequest, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Context-aware question answering via the Doubt Solver."""
    from app.services.open_library_service import get_book_detail
    try:
        book_data = await get_book_detail(payload.book_id)
        context = f"Book Title: {book_data.get('title')}\nDescription: {book_data.get('description')}"
    except Exception:
        context = f"Book ID: {payload.book_id}"

    page_text = f"{context}\nStudent is on Page {payload.page_number}."
    
    result = await ai_engine.solve_doubt(payload.question, page_text)
    
    return DoubtResponse(
        answer=result.get("answer", "Unable to generate answer."),
        source_page=payload.page_number,
        confidence=result.get("confidence", 0.0),
    )


@router.post("/analyze")
async def analyze_page(payload: SummaryRequest, user: User = Depends(get_current_user)):
    """Combined analysis — returns summary + flashcards in one call."""
    page_text = f"Content from book {payload.book_id}, page {payload.page_number}."

    result = await ai_engine.analyze_content(page_text)

    return {
        "book_id": payload.book_id,
        "page_number": payload.page_number,
        "summary": result.get("summary", ""),
        "key_points": result.get("key_points", []),
        "flashcards": result.get("flashcards", []),
    }


@router.post("/keywords")
async def extract_keywords(payload: SummaryRequest, user: User = Depends(get_current_user)):
    """Extract key terms and concepts from a page using AI."""
    # Check cache first (LAW 4: AI Rate Limiting)
    cache_key = f"ai:keywords:{payload.book_id}:{payload.page_number}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    page_text = f"Content from book {payload.book_id}, page {payload.page_number}."

    keywords = await ai_engine.extract_keywords(page_text)

    response_data = {
        "book_id": payload.book_id,
        "page_number": payload.page_number,
        "keywords": keywords,
    }

    # Cache the result for 24 hours
    cache_set(cache_key, response_data, AI_CACHE_TTL)

    return response_data


@router.get("/ai-status")
async def ai_status():
    """Check if AI features are available."""
    return {
        "available": ai_engine._is_available(),
        "model": "gpt-4o-mini",
        "message": "AI is ready!" if ai_engine._is_available() else "OPENAI_API_KEY not configured. AI returns mock data.",
    }


@router.post("/library-chat", response_model=LibraryChatResponse)
async def library_chat(
    payload: LibraryChatRequest, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """AI Assistant that queries across the user's entire library."""
    # 1. Fetch user's books to build library context
    stmt = select(Book).where(Book.user_id == user.id)
    result = await db.execute(stmt)
    books = result.scalars().all()
    
    # 2. Build context string
    context_parts = []
    for b in books:
        context_parts.append(f"Title: {b.title}, Author: {b.author}, Genre: {b.genre}")
    
    library_context = "\n".join(context_parts) if context_parts else "No books in library yet."
    
    # 3. Call AI engine
    ai_result = await ai_engine.library_chat(payload.query, library_context)
    
    return LibraryChatResponse(
        answer=ai_result.get("answer", "I couldn't find anything in your library."),
        suggested_books=ai_result.get("suggested_books", [])
    )
