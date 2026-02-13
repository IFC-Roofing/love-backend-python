"""
Contact CRUD operations.
"""
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session

from app.model.contact import Contact
from app.crud.base import CRUDBase


class CRUDContact(CRUDBase[Contact, dict, dict]):
    """Contact CRUD."""

    def get_by_user_and_id(
        self, db: Session, *, user_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Optional[Contact]:
        """Get a contact by id only if it belongs to the user."""
        return (
            db.query(self.model)
            .filter(self.model.id == contact_id, self.model.user_id == user_id)
            .first()
        )

    def list_by_user(self, db: Session, *, user_id: uuid.UUID) -> List[Contact]:
        """List all contacts for a user."""
        return db.query(self.model).filter(self.model.user_id == user_id).all()


contact_crud = CRUDContact(Contact)
