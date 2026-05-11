"""
Auth Schemas — Request/Response Models
========================================
"""

from typing import Literal

from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["student", "teacher", "admin"] = "student"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    name: str


class RefreshRequest(BaseModel):
    refresh_token: str
