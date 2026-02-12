"""
User CRUD operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.model.user import User
from app.schema.user import UserCreate
from app.crud.base import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, dict]):
    """User-specific CRUD operations."""
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return self.get_by_field(db, "email", email)

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create user record. Cognito handles passwords."""
        return self.create_from_dict(db, obj_in=obj_in.model_dump(exclude={"password"}))


user_crud = CRUDUser(User)
