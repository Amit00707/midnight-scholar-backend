"""
Flashcard Routes — Full CRUD + Review + Stats
================================================
Endpoints for generating, managing, reviewing, and analyzing flashcards
with SM-2 spaced repetition scheduling.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.database.models.user import User
from app.database.models.flashcard import Flashcard, ReviewLog
from app.database.models.gamification import Points
from app.schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardCreateRequest,
    FlashcardUpdateRequest,
    ReviewRequest,
    FlashcardOut,
    FlashcardListResponse,
    ReviewResponse,
    FlashcardStats,
    GenerateResponse,
)
from app.services import ai_engine
from app.services.spaced_repetition import sm2_update, preview_intervals

router = APIRouter(tags=["Flashcards"])


# ─── Helpers ─────────────────────────────────────────────────

def _card_to_out(card: Flashcard, include_previews: bool = False) -> FlashcardOut:
    """Convert a Flashcard ORM instance to the response schema."""
    previews = None
    if include_previews:
        previews = preview_intervals(card.ease_factor, card.interval, card.repetitions)

    return FlashcardOut(
        id=card.id,
        front=card.front,
        back=card.back,
        book_id=card.book_id,
        source_page=card.source_page,
        source=card.source or "ai",
        tags=card.tags,
        ease_factor=card.ease_factor,
        interval=card.interval,
        repetitions=card.repetitions,
        next_review=card.next_review,
        last_reviewed=card.last_reviewed,
        is_suspended=card.is_suspended or False,
        created_at=card.created_at,
        interval_previews=previews,
    )


# ─── Generate + Save ────────────────────────────────────────

@router.post("/flashcards/generate", response_model=GenerateResponse)
async def generate_flashcards(
    payload: FlashcardGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI flashcards from a page and persist them to the user's deck."""
    page_text = f"Content from book {payload.book_id}, page {payload.page_number}."
    if payload.context:
        page_text = f"SPECIFIC CONTEXT from page {payload.page_number}: {payload.context}\n\nGeneral context: {page_text}"

    # Generate via AI engine
    raw_cards = await ai_engine.generate_flashcards(page_text)

    # Check for existing cards on this page to avoid duplicates
    existing_q = await db.execute(
        select(Flashcard.front).where(
            and_(
                Flashcard.user_id == user.id,
                Flashcard.book_id == payload.book_id,
                Flashcard.source_page == payload.page_number,
            )
        )
    )
    existing_fronts = {row[0].lower().strip() for row in existing_q.fetchall()}

    new_cards = []
    duplicate_count = 0

    for card_data in raw_cards:
        front = card_data.get("front", "").strip()
        back = card_data.get("back", "").strip()

        if not front or not back:
            continue

        # Simple dedup by front text
        if front.lower().strip() in existing_fronts:
            duplicate_count += 1
            continue

        card = Flashcard(
            user_id=user.id,
            book_id=payload.book_id,
            source_page=payload.page_number,
            front=front,
            back=back,
            source="ai",
            ease_factor=2.5,
            interval=0,
            repetitions=0,
        )
        db.add(card)
        new_cards.append(card)
        existing_fronts.add(front.lower().strip())

    await db.commit()

    # Refresh to get IDs and timestamps
    for card in new_cards:
        await db.refresh(card)

    return GenerateResponse(
        book_id=payload.book_id,
        page_number=payload.page_number,
        flashcards=[_card_to_out(c, include_previews=True) for c in new_cards],
        new_count=len(new_cards),
        duplicate_count=duplicate_count,
    )


# ─── Get Due Cards ──────────────────────────────────────────

@router.get("/flashcards/due", response_model=FlashcardListResponse)
async def get_due_flashcards(
    book_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get flashcards that are due for review right now."""
    now = datetime.now(timezone.utc)

    query = select(Flashcard).where(
        and_(
            Flashcard.user_id == user.id,
            Flashcard.is_suspended == False,
            Flashcard.next_review <= now,
        )
    ).order_by(Flashcard.next_review.asc()).limit(limit)

    if book_id:
        query = query.where(Flashcard.book_id == book_id)

    result = await db.execute(query)
    cards = result.scalars().all()

    return FlashcardListResponse(
        flashcards=[_card_to_out(c, include_previews=True) for c in cards],
        total=len(cards),
    )


# ─── Get Deck (All Cards) ───────────────────────────────────

@router.get("/flashcards/deck", response_model=FlashcardListResponse)
async def get_deck(
    book_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all flashcards in the user's deck, optionally filtered by book."""
    query = select(Flashcard).where(Flashcard.user_id == user.id)

    if book_id:
        query = query.where(Flashcard.book_id == book_id)

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(Flashcard.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    cards = result.scalars().all()

    return FlashcardListResponse(
        flashcards=[_card_to_out(c) for c in cards],
        total=total,
    )


# ─── Review a Card ──────────────────────────────────────────

@router.post("/flashcards/{card_id}/review", response_model=ReviewResponse)
async def review_flashcard(
    card_id: int,
    payload: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a review rating for a flashcard. Triggers SM-2 scheduling."""
    result = await db.execute(
        select(Flashcard).where(
            and_(Flashcard.id == card_id, Flashcard.user_id == user.id)
        )
    )
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found.")

    # Run SM-2 algorithm
    updates = sm2_update(
        ease_factor=card.ease_factor,
        interval=card.interval,
        repetitions=card.repetitions,
        rating=payload.rating,
    )

    # Apply updates to card
    card.ease_factor = updates["ease_factor"]
    card.interval = updates["interval"]
    card.repetitions = updates["repetitions"]
    card.next_review = updates["next_review"]
    card.last_reviewed = updates["last_reviewed"]

    # Log the review
    log = ReviewLog(
        user_id=user.id,
        flashcard_id=card.id,
        rating=payload.rating,
        time_spent_ms=payload.time_spent_ms,
        ease_factor_after=updates["ease_factor"],
        interval_after=updates["interval"],
    )
    db.add(log)

    # ── Award XP points based on review quality ──
    xp_map = {0: 3, 1: 5, 2: 10, 3: 15}  # Again=3, Hard=5, Good=10, Easy=15
    points_earned = xp_map.get(payload.rating, 5)
    xp_record = Points(
        user_id=user.id,
        amount=points_earned,
        reason="flashcard_review",
    )
    db.add(xp_record)

    await db.commit()

    return ReviewResponse(
        flashcard_id=card.id,
        new_interval=updates["interval"],
        new_ease_factor=updates["ease_factor"],
        next_review=updates["next_review"],
        points_earned=points_earned,
    )


# ─── Manual Card Creation ───────────────────────────────────

@router.post("/flashcards/manual", response_model=FlashcardOut)
async def create_manual_flashcard(
    payload: FlashcardCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually create a flashcard."""
    card = Flashcard(
        user_id=user.id,
        book_id=payload.book_id,
        source_page=payload.source_page,
        front=payload.front,
        back=payload.back,
        tags=payload.tags,
        source="manual",
        ease_factor=2.5,
        interval=0,
        repetitions=0,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    return _card_to_out(card, include_previews=True)


# ─── Update Card ────────────────────────────────────────────

@router.put("/flashcards/{card_id}", response_model=FlashcardOut)
async def update_flashcard(
    card_id: int,
    payload: FlashcardUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit an existing flashcard."""
    result = await db.execute(
        select(Flashcard).where(
            and_(Flashcard.id == card_id, Flashcard.user_id == user.id)
        )
    )
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found.")

    if payload.front is not None:
        card.front = payload.front
    if payload.back is not None:
        card.back = payload.back
    if payload.tags is not None:
        card.tags = payload.tags
    if payload.is_suspended is not None:
        card.is_suspended = payload.is_suspended

    await db.commit()
    await db.refresh(card)

    return _card_to_out(card)


# ─── Delete Card ────────────────────────────────────────────

@router.delete("/flashcards/{card_id}")
async def delete_flashcard(
    card_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a flashcard and its review history."""
    result = await db.execute(
        select(Flashcard).where(
            and_(Flashcard.id == card_id, Flashcard.user_id == user.id)
        )
    )
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found.")

    await db.delete(card)
    await db.commit()

    return {"detail": "Flashcard deleted."}


# ─── Suspend / Unsuspend ────────────────────────────────────

@router.post("/flashcards/{card_id}/suspend")
async def toggle_suspend(
    card_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle suspend state of a flashcard."""
    result = await db.execute(
        select(Flashcard).where(
            and_(Flashcard.id == card_id, Flashcard.user_id == user.id)
        )
    )
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found.")

    card.is_suspended = not card.is_suspended
    await db.commit()

    return {"id": card.id, "is_suspended": card.is_suspended}


# ─── Stats ──────────────────────────────────────────────────

@router.get("/flashcards/stats", response_model=FlashcardStats)
async def get_flashcard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive flashcard statistics for the user."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)

    # Base query for user's cards
    base = select(Flashcard).where(Flashcard.user_id == user.id)

    # Total cards
    total_q = select(func.count()).select_from(base.subquery())
    total_cards = (await db.execute(total_q)).scalar() or 0

    # Due today
    due_q = select(func.count()).where(
        and_(
            Flashcard.user_id == user.id,
            Flashcard.is_suspended == False,
            Flashcard.next_review <= now,
        )
    )
    due_today = (await db.execute(due_q)).scalar() or 0

    # Cards reviewed today
    reviewed_today_q = select(func.count()).where(
        and_(
            ReviewLog.user_id == user.id,
            ReviewLog.reviewed_at >= today_start,
        )
    )
    cards_reviewed_today = (await db.execute(reviewed_today_q)).scalar() or 0

    # Average ease factor
    avg_ease_q = select(func.avg(Flashcard.ease_factor)).where(
        Flashcard.user_id == user.id
    )
    average_ease = (await db.execute(avg_ease_q)).scalar() or 2.5

    # Mature vs young vs new
    mature_q = select(func.count()).where(
        and_(Flashcard.user_id == user.id, Flashcard.interval > 21)
    )
    mature_cards = (await db.execute(mature_q)).scalar() or 0

    new_q = select(func.count()).where(
        and_(Flashcard.user_id == user.id, Flashcard.repetitions == 0)
    )
    new_cards = (await db.execute(new_q)).scalar() or 0

    young_cards = total_cards - mature_cards - new_cards

    # Suspended count
    suspended_q = select(func.count()).where(
        and_(Flashcard.user_id == user.id, Flashcard.is_suspended == True)
    )
    suspended_cards = (await db.execute(suspended_q)).scalar() or 0

    # Retention rate (% of Good/Easy in last 30 days)
    total_reviews_q = select(func.count()).where(
        and_(
            ReviewLog.user_id == user.id,
            ReviewLog.reviewed_at >= thirty_days_ago,
        )
    )
    total_reviews = (await db.execute(total_reviews_q)).scalar() or 0

    good_easy_q = select(func.count()).where(
        and_(
            ReviewLog.user_id == user.id,
            ReviewLog.reviewed_at >= thirty_days_ago,
            ReviewLog.rating >= 2,
        )
    )
    good_easy = (await db.execute(good_easy_q)).scalar() or 0

    retention_rate = (good_easy / total_reviews * 100) if total_reviews > 0 else 0.0

    # Per-book breakdown
    books_q = select(
        Flashcard.book_id,
        func.count().label("card_count"),
    ).where(
        Flashcard.user_id == user.id
    ).group_by(Flashcard.book_id)

    books_result = await db.execute(books_q)
    books_data = []
    for row in books_result.fetchall():
        # Count due per book
        book_due_q = select(func.count()).where(
            and_(
                Flashcard.user_id == user.id,
                Flashcard.book_id == row[0],
                Flashcard.is_suspended == False,
                Flashcard.next_review <= now,
            )
        )
        book_due = (await db.execute(book_due_q)).scalar() or 0
        books_data.append({
            "book_id": row[0],
            "card_count": row[1],
            "due_count": book_due,
        })

    return FlashcardStats(
        total_cards=total_cards,
        due_today=due_today,
        cards_reviewed_today=cards_reviewed_today,
        average_ease=round(average_ease, 2),
        mature_cards=mature_cards,
        young_cards=max(0, young_cards),
        new_cards=new_cards,
        suspended_cards=suspended_cards,
        retention_rate=round(retention_rate, 1),
        books=books_data,
    )
