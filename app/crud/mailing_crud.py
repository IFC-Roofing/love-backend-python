"""
Mailing CRUD.
"""
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.model.mailing import Mailing
from app.crud.base import CRUDBase


class CRUDMailing(CRUDBase[Mailing, dict, dict]):
    def create_from_dict(self, db: Session, *, obj_in: dict) -> Mailing:
        return super().create_from_dict(db, obj_in=obj_in)

    def get_by_user_and_id(self, db: Session, *, user_id: uuid.UUID, mailing_id: uuid.UUID) -> Optional[Mailing]:
        return db.query(self.model).filter(self.model.id == mailing_id, self.model.user_id == user_id).first()

    def list_by_user_paginated(
        self, db: Session, *, user_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> Tuple[List[Mailing], int]:
        base = db.query(self.model).filter(self.model.user_id == user_id)
        total = base.with_entities(func.count(self.model.id)).scalar() or 0
        skip = (page - 1) * limit
        items = base.order_by(desc(self.model.created_at)).offset(skip).limit(limit).all()
        return items, total

    def list_pending_with_external_id(
        self, db: Session, *, user_id: Optional[uuid.UUID] = None, limit: int = 50
    ) -> List[Mailing]:
        q = db.query(self.model).filter(
            self.model.external_id.isnot(None),
            self.model.external_id != "",
            ~self.model.status.in_(["sent", "canceled", "cancelled"]),
        )
        if user_id is not None:
            q = q.filter(self.model.user_id == user_id)
        return q.order_by(self.model.created_at).limit(limit).all()


mailing_crud = CRUDMailing(Mailing)
