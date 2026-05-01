"""
AI Routes — /summary /quiz /flashcards /ask
==============================================
All AI endpoints use the ai_engine service which gracefully
falls back to mock data when OPENAI_API_KEY is not set.
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.database.models.user import User
from app.schemas.ai import AskRequest, SummaryRequest, SummaryResponse, QuizResponse, FlashcardResponse, DoubtResponse
from app.services import ai_engine

router = APIRouter()


@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(payload: SummaryRequest, user: User = Depends(get_current_user)):
    """Generate an AI summary of the current page."""
    # In production, fetch the actual page text from the book's PDF/content
    # For now, we use a placeholder that the AI engine can work with
    page_text = f"Content from book {payload.book_id}, page {payload.page_number}."
    
    result = await ai_engine.generate_summary(page_text)
    
    return SummaryResponse(
        summary=result.get("summary", ""),
        key_points=result.get("key_points", []),
        page_number=payload.page_number,
    )


@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(payload: SummaryRequest, user: User = Depends(get_current_user)):
    """Generate AI-powered quiz questions from a page."""
    page_text = f"Content from book {payload.book_id}, page {payload.page_number}."
    
    questions = await ai_engine.generate_quiz(page_text)
    
    return QuizResponse(book_id=payload.book_id, questions=questions)


@router.post("/flashcards", response_model=FlashcardResponse)
async def generate_flashcards(payload: SummaryRequest, user: User = Depends(get_current_user)):
    """Generate spaced-repetition flashcards from a page."""
    page_text = f"Content from book {payload.book_id}, page {payload.page_number}."
    
    flashcards = await ai_engine.generate_flashcards(page_text)
    
    return FlashcardResponse(book_id=payload.book_id, flashcards=flashcards)


@router.post("/ask", response_model=DoubtResponse)
async def ask_doubt(payload: AskRequest, user: User = Depends(get_current_user)):
    """Context-aware question answering via the Doubt Solver."""
    page_text = f"Content from book {payload.book_id}, page {payload.page_number}."
    
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


@router.get("/ai-status")
async def ai_status():
    """Check if AI features are available."""
    return {
        "available": ai_engine._is_available(),
        "model": "gpt-4o-mini",
        "message": "AI is ready!" if ai_engine._is_available() else "OPENAI_API_KEY not configured. AI returns mock data.",
    }
