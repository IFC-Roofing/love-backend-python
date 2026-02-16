"""
User service.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.crud import user_crud
from app.core.exceptions import NotFound
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Handles user-related operations."""
    
    def __init__(self, db: Session):
        self.db = db

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile by ID."""
        user = user_crud.get(self.db, user_id)
        
        if not user:
            raise NotFound("User")
        
        return {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "profile_image_url": getattr(user, "profile_image_url", None),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
