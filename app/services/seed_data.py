"""
Seed Data Script — Populates initial data for plans and gamification
Run with: python -m app.services.seed_data
"""

import asyncio
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory
from app.database.models.subscription import Plan
from app.database.models.gamification import Badge


PLANS = [
    {
        "name": "Free",
        "price_monthly": 0.0,
        "price_yearly": 0.0,
        "max_books": 3,
        "ai_queries_per_day": 5,
        "features": json.dumps([
            "Access to 100,000+ free books",
            "Basic flashcard system",
            "Limited AI queries per day",
            "Community features"
        ])
    },
    {
        "name": "Scholar",
        "price_monthly": 9.99,
        "price_yearly": 99.0,
        "max_books": 50,
        "ai_queries_per_day": 50,
        "features": json.dumps([
            "Everything in Free",
            "Unlimited books",
            "Full AI features",
            "Spaced repetition analytics",
            "Teacher dashboard",
            "Priority support"
        ])
    },
    {
        "name": "Academy",
        "price_monthly": 24.99,
        "price_yearly": 249.0,
        "max_books": 500,
        "ai_queries_per_day": 200,
        "features": json.dumps([
            "Everything in Scholar",
            "Classroom management",
            "Student progress tracking",
            "Custom quizzes",
            "API access",
            "Dedicated support",
            "White-label options"
        ])
    }
]


BADGES = [
    {"name": "First Steps", "icon_url": "🌱", "description": "Complete your first book", "requirement_type": "books_completed", "requirement_value": 1},
    {"name": "Bookworm", "icon_url": "📚", "description": "Complete 10 books", "requirement_type": "books_completed", "requirement_value": 10},
    {"name": "Scholar", "icon_url": "🎓", "description": "Complete 50 books", "requirement_type": "books_completed", "requirement_value": 50},
    {"name": "Library Legend", "icon_url": "📖", "description": "Complete 100 books", "requirement_type": "books_completed", "requirement_value": 100},
    {"name": "Flashcard Rookie", "icon_url": "🃏", "description": "Review 100 flashcards", "requirement_type": "cards_reviewed", "requirement_value": 100},
    {"name": "Memory Master", "icon_url": "🧠", "description": "Review 1000 flashcards", "requirement_type": "cards_reviewed", "requirement_value": 1000},
    {"name": "Quiz Whiz", "icon_url": "🧩", "description": "Score 100% on 10 quizzes", "requirement_type": "perfect_quizzes", "requirement_value": 10},
    {"name": "Early Bird", "icon_url": "🌅", "description": "Read for 7 days in a row", "requirement_type": "streak_days", "requirement_value": 7},
    {"name": "Week Warrior", "icon_url": "🔥", "description": "Read for 30 days in a row", "requirement_type": "streak_days", "requirement_value": 30},
    {"name": "Century Club", "icon_url": "💯", "description": "Earn 100 points", "requirement_type": "total_points", "requirement_value": 100},
    {"name": "Knowledge Seeker", "icon_url": "⭐", "description": "Earn 1000 points", "requirement_type": "total_points", "requirement_value": 1000},
    {"name": "Wisdom Keeper", "icon_url": "🌟", "description": "Earn 10000 points", "requirement_type": "total_points", "requirement_value": 10000},
]


async def seed_plans(db: AsyncSession):
    """Seed subscription plans."""
    print("Seeding plans...")

    # Check if plans already exist
    result = await db.execute(select(Plan))
    existing = result.scalars().all()

    if existing:
        print(f"Plans already exist ({len(existing)}), skipping...")
        return

    for plan_data in PLANS:
        plan = Plan(**plan_data)
        db.add(plan)

    await db.commit()
    print(f"[OK] Created {len(PLANS)} plans")


async def seed_badges(db: AsyncSession):
    """Seed gamification badges."""
    print("Seeding badges...")

    # Check if badges already exist
    result = await db.execute(select(Badge))
    existing = result.scalars().all()

    if existing:
        print(f"Badges already exist ({len(existing)}), skipping...")
        return

    for badge_data in BADGES:
        badge = Badge(**badge_data)
        db.add(badge)

    await db.commit()
    print(f"[OK] Created {len(BADGES)} badges")


async def seed_all():
    """Run all seed functions."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        await seed_plans(db)
        await seed_badges(db)
    print("\n[DONE] Seed data complete!")
    print("   - Plans: Free, Scholar, Academy")
    print("   - Badges: 12 achievement badges")


if __name__ == "__main__":
    asyncio.run(seed_all())