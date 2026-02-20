"""
Contact CRUD operations.
"""
from typing import List, Optional, Tuple
import uuid
from sqlalchemy import func, or_
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

    def get_by_user_and_email(
        self, db: Session, *, user_id: uuid.UUID, email: str
    ) -> Optional[Contact]:
        """Get a contact by user and email (for upsert/sync)."""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id, self.model.email == email)
            .first()
        )

    def list_by_user(self, db: Session, *, user_id: uuid.UUID) -> List[Contact]:
        """List all contacts for a user."""
        return db.query(self.model).filter(self.model.user_id == user_id).all()

    def list_by_user_paginated(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Tuple[List[Contact], int]:
        """
        List contacts for a user with pagination and optional filters.
        search: ILIKE on name or email (optional).
        name: ILIKE on name (optional).
        email: ILIKE on email (optional).
        Returns (contacts, total_count).
        """
        base = db.query(self.model).filter(self.model.user_id == user_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            base = base.filter(
                or_(
                    self.model.name.ilike(term),
                    self.model.email.ilike(term),
                )
            )
        if name is not None and name.strip():
            base = base.filter(self.model.name.ilike(f"%{name.strip()}%"))
        if email is not None and email.strip():
            base = base.filter(self.model.email.ilike(f"%{email.strip()}%"))

        total = base.with_entities(func.count(self.model.id)).scalar() or 0
        contacts = base.order_by(self.model.email).offset(offset).limit(limit).all()
        return contacts, total


contact_crud = CRUDContact(Contact)
