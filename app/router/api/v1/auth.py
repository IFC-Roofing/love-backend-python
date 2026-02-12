"""
Authentication router - login/logout/register.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import validate_session, get_current_token
from app.core.exceptions import InvalidCredentials
from app.service.auth_service import AuthService
from app.schema.auth import UserRegister, UserLogin, LoginResponse, MessageResponse, VerifyEmail, ResendCode, ForgotPassword, ResetPassword, ChangePassword
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=MessageResponse)
async def signup(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthService(db)
    auth_service.register_user(user_data)
    return MessageResponse(message="User registered successfully")


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login and get JWT token."""
    auth_service = AuthService(db)
    return auth_service.login(login_data)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db)
):
    """Logout - invalidates token server-side and signs out from Cognito."""
    auth_service = AuthService(db)
    token = get_current_token(request)
    auth_service.logout(token, current_user)
    logger.info(f"User logged out: {current_user['email']}")
    return MessageResponse(message="Logged out successfully")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    data: VerifyEmail,
    db: Session = Depends(get_db)
):
    """Verify email with confirmation code sent after signup."""
    auth_service = AuthService(db)
    auth_service.verify_email(data.email, data.code)
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-code", response_model=MessageResponse)
async def resend_code(
    data: ResendCode,
    db: Session = Depends(get_db)
):
    """Resend email verification code."""
    auth_service = AuthService(db)
    auth_service.resend_verification_code(data.email)
    return MessageResponse(message="Verification code resent")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPassword,
    db: Session = Depends(get_db)
):
    """Initiate forgot password flow - sends reset code to email."""
    auth_service = AuthService(db)
    auth_service.forgot_password(data.email)
    return MessageResponse(message="Password reset code sent to email")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPassword,
    db: Session = Depends(get_db)
):
    """Reset password with code from forgot-password flow."""
    auth_service = AuthService(db)
    auth_service.reset_password(data.email, data.code, data.new_password)
    return MessageResponse(message="Password reset successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePassword,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db)
):
    """Change password for logged-in user (requires current password)."""
    auth_service = AuthService(db)
    access_token = current_user.get('access_token')
    if not access_token:
        raise InvalidCredentials(message="Access token not found in session")
    
    auth_service.change_password(access_token, data.current_password, data.new_password)
    logger.info(f"Password changed for user: {current_user['email']}")
    return MessageResponse(message="Password changed successfully")
