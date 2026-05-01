"""
AI Engine Service — OpenAI Integration
=====================================================
Handles LLM calls for summary, quiz, flashcard generation, and doubt solving.
Gracefully degrades when OPENAI_API_KEY is not configured.
"""

import json
import logging
from typing import List, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── OpenAI Client Setup ──────────────────────────────────────
_client = None

def _get_client():
    """Lazy-load the OpenAI client only when needed."""
    global _client
    if _client is not None:
        return _client

    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your"):
        logger.warning("OPENAI_API_KEY not configured — AI features will return mock data.")
        return None

    try:
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully.")
        return _client
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        return None


def _is_available() -> bool:
    """Check if OpenAI is configured and ready."""
    return _get_client() is not None


# ─── Summary Generation ──────────────────────────────────────
async def generate_summary(page_text: str) -> Dict:
    """Generate a concise summary of a page's content."""
    client = _get_client()
    if not client:
        return _mock_summary(page_text)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize the following content in a clear and structured way.\n\n"
                        "Rules:\n"
                        "- Use bullet points\n"
                        "- Cover key ideas only\n"
                        "- Keep it short (100 to 150 words)\n"
                        "- Use simple language\n\n"
                        "Return ONLY valid JSON: {\"summary\": \"your bullet-point summary here\", \"key_points\": [\"point1\", \"point2\", \"point3\"]}"
                    ),
                },
                {"role": "user", "content": page_text[:4000]},  # Limit to ~4k chars
            ],
        )
        content = response.choices[0].message.content.strip()
        # Try to parse as JSON
        result = _safe_parse_json(content)
        if result:
            return result
        return {"summary": content, "key_points": []}
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return _mock_summary(page_text)


# ─── Quiz Generation ─────────────────────────────────────────
async def generate_quiz(page_text: str, num_questions: int = 3) -> List[Dict]:
    """Generate multiple-choice quiz questions from page content."""
    client = _get_client()
    if not client:
        return _mock_quiz()

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.5,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Create high-quality quiz questions for learning.\n\n"
                        "Rules:\n"
                        "- Generate 8 multiple-choice questions\n"
                        "- Mix types: Definition, Concept, Example\n"
                        "- Each question has 4 options with 1 correct answer\n\n"
                        "Return ONLY a valid JSON array. Each object must have: "
                        "\"question\" (string), \"options\" (array of 4 strings), \"correct_answer\" (0-indexed int). "
                        "Example: [{\"question\": \"What is X?\", \"options\": [\"A\",\"B\",\"C\",\"D\"], \"correct_answer\": 0}]"
                    ),
                },
                {"role": "user", "content": page_text[:4000]},
            ],
        )
        content = response.choices[0].message.content.strip()
        result = _safe_parse_json(content)
        if isinstance(result, list):
            return result
        return _mock_quiz()
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        return _mock_quiz()


# ─── Flashcard Generation ────────────────────────────────────
async def generate_flashcards(page_text: str) -> List[Dict]:
    """Generate spaced-repetition flashcards from page content."""
    client = _get_client()
    if not client:
        return _mock_flashcards()

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Create flashcards from the following content.\n\n"
                        "Rules:\n"
                        "- Generate 5 to 10 flashcards\n"
                        "- Each flashcard has a Question and an Answer\n"
                        "- Keep answers short\n"
                        "- Focus on key concepts\n\n"
                        "Return ONLY a valid JSON array. Each object must have: "
                        "\"front\" (question) and \"back\" (answer). "
                        "Example: [{\"front\": \"What is X?\", \"back\": \"X is...\"}]"
                    ),
                },
                {"role": "user", "content": page_text[:4000]},
            ],
        )
        content = response.choices[0].message.content.strip()
        result = _safe_parse_json(content)
        if isinstance(result, list):
            return result
        return _mock_flashcards()
    except Exception as e:
        logger.error(f"Flashcard generation failed: {e}")
        return _mock_flashcards()


# ─── Combined Analysis (Summary + Flashcards) ────────────────
async def analyze_content(page_text: str) -> Dict:
    """Analyze content and return both a summary and flashcards in one call."""
    client = _get_client()
    if not client:
        mock_summary = _mock_summary(page_text)
        mock_cards = _mock_flashcards()
        return {"summary": mock_summary["summary"], "key_points": mock_summary["key_points"], "flashcards": mock_cards}

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze the content and return:\n\n"
                        "1. Summary (short bullet points)\n"
                        "2. 5 flashcards\n\n"
                        "Return ONLY valid JSON:\n"
                        "{\"summary\": \"bullet point summary\", "
                        "\"key_points\": [\"point1\", \"point2\", \"point3\"], "
                        "\"flashcards\": [{\"front\": \"Q1\", \"back\": \"A1\"}]}"
                    ),
                },
                {"role": "user", "content": page_text[:4000]},
            ],
        )
        content = response.choices[0].message.content.strip()
        result = _safe_parse_json(content)
        if result and "summary" in result:
            return result
        return {"summary": content, "key_points": [], "flashcards": []}
    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        mock_summary = _mock_summary(page_text)
        return {"summary": mock_summary["summary"], "key_points": mock_summary["key_points"], "flashcards": _mock_flashcards()}


# ─── Doubt Solver ─────────────────────────────────────────────
async def solve_doubt(question: str, page_text: str) -> Dict:
    """Context-aware question answering — the Doubt Solver."""
    client = _get_client()
    if not client:
        return _mock_doubt(question)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert tutor. Explain the user question in a clear and simple way.\n\n"
                        "Rules:\n"
                        "- Use step-by-step explanation\n"
                        "- Use examples\n"
                        "- Keep answer short and clear\n"
                        "- If math or coding, show steps\n"
                        "- Avoid complex words\n\n"
                        "Use the provided page context to answer accurately. "
                        "Return ONLY valid JSON: {\"answer\": \"your explanation here\", \"confidence\": 0.95}"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Page Context:\n{page_text[:3000]}\n\nStudent Question: {question}",
                },
            ],
        )
        content = response.choices[0].message.content.strip()
        result = _safe_parse_json(content)
        if result and "answer" in result:
            return result
        return {"answer": content, "confidence": 0.8}
    except Exception as e:
        logger.error(f"Doubt solver failed: {e}")
        return _mock_doubt(question)


# ─── JSON Parser ──────────────────────────────────────────────
def _safe_parse_json(text: str) -> Optional[any]:
    """Safely parse JSON from LLM output, handling markdown code fences."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


# ─── Mock Data (when API key is missing) ──────────────────────
def _mock_summary(text: str) -> Dict:
    preview = text[:100] if text else "No text provided"
    return {
        "summary": f"[AI not configured] This page discusses key concepts related to the subject matter. Preview: {preview}...",
        "key_points": [
            "Configure OPENAI_API_KEY in .env for real AI summaries",
            "AI features include summary, quiz, flashcards, and doubt solving",
            "Visit platform.openai.com to get your API key",
        ],
    }


def _mock_quiz() -> List[Dict]:
    return [
        {
            "question": "What feature generates AI-powered quizzes in Midnight Scholar?",
            "options": ["Quiz Generator", "Flashcard Maker", "Summary Tool", "Doubt Solver"],
            "correct_answer": 0,
        },
        {
            "question": "Which API key is needed for AI features?",
            "options": ["AWS Key", "OpenAI Key", "Google Key", "Stripe Key"],
            "correct_answer": 1,
        },
        {
            "question": "What model does Midnight Scholar use by default?",
            "options": ["GPT-3.5", "GPT-4o-mini", "Claude 3", "Gemini Pro"],
            "correct_answer": 1,
        },
    ]


def _mock_flashcards() -> List[Dict]:
    return [
        {"front": "What is Midnight Scholar?", "back": "An AI-powered e-book reading platform."},
        {"front": "What does the Doubt Solver do?", "back": "Answers questions about the book you are reading using AI."},
        {"front": "What is spaced repetition?", "back": "A learning technique that increases review intervals over time."},
        {"front": "What AI model powers the platform?", "back": "OpenAI GPT-4o-mini (configurable)."},
        {"front": "How to enable AI features?", "back": "Add your OPENAI_API_KEY to the .env file."},
    ]


def _mock_doubt(question: str) -> Dict:
    return {
        "answer": f"[AI not configured] To answer your question \"{question}\", please configure the OPENAI_API_KEY in your .env file. Visit platform.openai.com to get your API key.",
        "confidence": 0.0,
    }
