"""
Subscription Routes — /plans /checkout /webhook /cancel
=========================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.database.models.subscription import Plan
from app.core.dependencies import get_current_user
from app.database.models.user import User

router = APIRouter()


@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all available subscription plans."""
    result = await db.execute(select(Plan))
    plans = result.scalars().all()
    return {"plans": [{"id": p.id, "name": p.name, "price_monthly": p.price_monthly} for p in plans]}


@router.post("/checkout")
async def create_checkout(plan_id: int, user: User = Depends(get_current_user)):
    """Create a Stripe checkout session."""
    # TODO: Integrate Stripe SDK
    return {"checkout_url": f"https://checkout.stripe.com/pay?plan={plan_id}"}


@router.post("/webhook")
async def stripe_webhook():
    """Handle Stripe webhook events (payment success, cancellation)."""
    # TODO: Verify Stripe signature and update subscription status
    return {"received": True}


@router.post("/cancel")
async def cancel_subscription(user: User = Depends(get_current_user)):
    """Cancel the current user's subscription."""
    # TODO: Update UserSubscription record
    return {"message": "Subscription cancelled"}
