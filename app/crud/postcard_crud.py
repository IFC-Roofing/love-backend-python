"""
Postcard CRUD operations.
"""
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.model.postcard import Postcard
from app.crud.base import CRUDBase


class CRUDPostcard(CRUDBase[Postcard, Dict[str, Any], Dict[str, Any]]):
    """Postcard CRUD with simple page/limit pagination."""

    def create_from_dict(self, db: Session, *, obj_in: Dict[str, Any]) -> Postcard:
        return super().create_from_dict(db, obj_in=obj_in)

    def get_by_user_and_id(self, db: Session, *, user_id: uuid.UUID, postcard_id: uuid.UUID) -> Optional[Postcard]:
        """Get a postcard by id only if it belongs to the user."""
        return (
            db.query(self.model)
            .filter(self.model.id == postcard_id, self.model.user_id == user_id)
            .first()
        )

    def get_by_id(self, db: Session, *, postcard_id: uuid.UUID) -> Optional[Postcard]:
        """Get a postcard by id (no user check). For testing without auth."""
        return db.query(self.model).filter(self.model.id == postcard_id).first()

    def list_by_user_paginated(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[Postcard], int]:
        """
        List postcards for a user with simple pagination (newest first).
        Returns (items, total_count). page is 1-based.
        """
        base = db.query(self.model).filter(self.model.user_id == user_id)
        total = base.with_entities(func.count(self.model.id)).scalar() or 0
        skip = (page - 1) * limit
        items = base.order_by(desc(self.model.id)).offset(skip).limit(limit).all()
        return items, total

    def list_paginated(
        self,
        db: Session,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[Postcard], int]:
        """
        List all postcards with pagination (newest first). For testing without auth.
        Returns (items, total_count). page is 1-based.
        """
        base = db.query(self.model)
        total = base.with_entities(func.count(self.model.id)).scalar() or 0
        skip = (page - 1) * limit
        items = base.order_by(desc(self.model.id)).offset(skip).limit(limit).all()
        return items, total


postcard_crud = CRUDPostcard(Postcard)
