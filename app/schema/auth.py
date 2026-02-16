"""
Authentication schemas.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class VerifyEmail(BaseModel):
    email: EmailStr
    code: str


class ResendCode(BaseModel):
    email: EmailStr


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class UserInfo(BaseModel):
    id: str
    email: str
    is_active: bool
    profile_image_url: Optional[str] = None


class UserProfile(UserInfo):
    """Extended user info with timestamps."""
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class MessageResponse(BaseModel):
    message: str


class SessionStatus(BaseModel):
    authenticated: bool
    user: Optional[UserInfo] = None
