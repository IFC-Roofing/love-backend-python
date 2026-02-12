"""
User router - profile endpoints (protected).
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import validate_session
from app.service.user_service import UserService
from app.schema.auth import UserProfile
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db)
):
    """Get current user profile. Session validated via validate_session dependency."""
    logger.info(f"Session active for user: {current_user['email']} (user_id: {current_user['user_id']})")
    user_service = UserService(db)
    return user_service.get_profile(current_user["user_id"])


@router.get("/session")
async def get_session_info(
    current_user: Dict[str, Any] = Depends(validate_session)
):
    """Return current session data. Proves session is working."""
    logger.info(f"Session info requested by: {current_user['email']}")
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "is_active": current_user["is_active"],
        "session_active": True
    }
