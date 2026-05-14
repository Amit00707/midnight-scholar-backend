"""
Auth Routes — /login /signup /verify /refresh
================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.database.session import get_db
from app.database.models.user import User, UserRole
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user
from app.schemas.auth import SignupRequest, LoginRequest, VerifyRequest, TokenResponse, RefreshRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check for existing email
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole(payload.role),
    )
    db.add(user)
    await db.flush()

    user_role = getattr(user.role, "value", user.role)
    access_token = create_access_token(data={"sub": str(user.id), "role": user_role})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user_role,
        user_id=user.id,
        name=user.name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a user and return JWT tokens."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_role = getattr(user.role, "value", user.role)
    access_token = create_access_token(data={"sub": str(user.id), "role": user_role})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user_role,
        user_id=user.id,
        name=user.name,
    )


@router.post("/forgot-password")
async def forgot_password(payload: dict, db: AsyncSession = Depends(get_db)):
    """Send a password reset email (mock — logs token, no real email yet)."""
    from pydantic import BaseModel
    email = payload.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if user:
        # In production: generate token, store in Redis, send email
        reset_token = create_access_token(data={"sub": str(user.id), "type": "reset"})
        logger.info(f"Password reset requested for {email}. Token: {reset_token[:20]}...")
    
    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(payload: dict, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid reset token."""
    token = payload.get("token", "")
    new_password = payload.get("new_password", "")
    
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new password are required")
    
    decoded = decode_token(token)
    if not decoded or decoded.get("type") != "reset":
        raise HTTPException(status_code=401, detail="Invalid or expired reset token")
    
    user_id = decoded.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = hash_password(new_password)
    return {"message": "Password reset successfully"}


@router.post("/verify")
async def verify_email(payload: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify a user's email address via OTP code."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # In production: Validate OTP against stored code in Redis
    # For now, we'll allow any 6-digit code for demonstration
    if len(payload.code) != 6:
        raise HTTPException(status_code=400, detail="Invalid verification code")
        
    user.is_verified = True
    await db.commit()
    return {"message": "Email verified successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = decoded.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_role = getattr(user.role, "value", user.role)
    new_access = create_access_token(data={"sub": str(user.id), "role": user_role})
    new_refresh = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        role=user_role,
        user_id=user.id,
        name=user.name,
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    current_role = getattr(current_user.role, "value", current_user.role)
    return {
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_role,
    }
