"""
User router - profile endpoints (protected).
"""
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import validate_session
from app.crud import user_crud
from app.service.user_service import UserService
from app.schema.auth import UserProfile
from app.aws.s3 import upload_to_s3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_PROFILE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db)
):
    """Get current user profile. Session validated via validate_session dependency."""
    logger.info(f"Session active for user: {current_user['email']} (user_id: {current_user['user_id']})")
    user_service = UserService(db)
    return user_service.get_profile(current_user["user_id"])


@router.patch("/me/profile-image", response_model=UserProfile)
async def update_profile_image(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """Upload profile image to S3 and set as user's profile_image_url. Requires S3_BUCKET_NAME."""
    if not settings.use_s3:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Profile image upload requires S3. Set S3_BUCKET_NAME.",
        )
    if file.content_type not in ALLOWED_PROFILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, WebP).",
        )
    user_id = uuid.UUID(current_user["user_id"])
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    ext = ".jpg"
    if file.filename:
        ext = "." + (file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg")
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"

    content = await file.read()
    key = f"users/{user_id}/profile{ext}"
    url = upload_to_s3(key=key, body=content, content_type=file.content_type or "image/jpeg")

    user_crud.update(db, db_obj=user, obj_in={"profile_image_url": url})
    db.refresh(user)
    return UserService(db).get_profile(current_user["user_id"])


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
