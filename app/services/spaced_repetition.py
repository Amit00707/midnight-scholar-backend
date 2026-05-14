"""
Spaced Repetition Service — SM-2 Algorithm
=============================================
Implements the SuperMemo 2 algorithm for scheduling flashcard reviews.

Rating scale:
  0 = Again  (complete failure, reset)
  1 = Hard   (correct but with difficulty)
  2 = Good   (correct with moderate effort)
  3 = Easy   (effortless recall)
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# Maximum interval cap to prevent cards from disappearing for too long.
MAX_INTERVAL_DAYS = 180

# Minimum ease factor — prevents death spirals.
MIN_EASE_FACTOR = 1.3


def sm2_update(
    ease_factor: float,
    interval: int,
    repetitions: int,
    rating: int,
) -> Dict[str, Any]:
    """
    Apply the SM-2 algorithm to compute the next review schedule.

    Args:
        ease_factor: Current ease factor (≥ 1.3, starts at 2.5).
        interval:    Current interval in days.
        repetitions: Number of consecutive successful reviews.
        rating:      User's self-assessment (0-3).

    Returns:
        Dict with updated fields: ease_factor, interval, repetitions,
        next_review, last_reviewed.
    """
    # Map our 0-3 scale to SM-2's 0-5 quality scale.
    quality_map = {0: 0, 1: 2, 2: 4, 3: 5}
    quality = quality_map.get(rating, 0)

    ef = ease_factor

    if quality < 3:
        # Failed — reset repetitions, short interval.
        repetitions = 0
        interval = 1
    else:
        # Passed — advance the schedule.
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        repetitions += 1

    # Update ease factor (never below MIN_EASE_FACTOR).
    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(MIN_EASE_FACTOR, ef)

    # Cap the interval.
    interval = min(interval, MAX_INTERVAL_DAYS)

    now = datetime.now(timezone.utc)

    return {
        "ease_factor": round(ef, 4),
        "interval": interval,
        "repetitions": repetitions,
        "next_review": now + timedelta(days=interval),
        "last_reviewed": now,
    }


def get_interval_display(interval: int) -> str:
    """Human-readable interval for the UI (e.g. '< 1m', '10m', '1d', '4d')."""
    if interval == 0:
        return "< 1m"
    elif interval == 1:
        return "1d"
    elif interval < 30:
        return f"{interval}d"
    elif interval < 365:
        months = interval // 30
        return f"{months}mo"
    else:
        years = interval // 365
        return f"{years}y"


def preview_intervals(
    ease_factor: float,
    interval: int,
    repetitions: int,
) -> Dict[int, str]:
    """
    Preview what each rating would produce — shown under the rating buttons.

    Returns:
        Dict mapping rating (0-3) to human-readable interval string.
    """
    previews = {}
    for rating in range(4):
        result = sm2_update(ease_factor, interval, repetitions, rating)
        previews[rating] = get_interval_display(result["interval"])
    return previews
