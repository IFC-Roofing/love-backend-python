"""
Chat message CRUD.
"""
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.model.chat_message import ChatMessage
from app.crud.base import CRUDBase


class CRUDChatMessage(CRUDBase[ChatMessage, Dict[str, Any], Dict[str, Any]]):
    def create_from_dict(self, db: Session, *, obj_in: Dict[str, Any]) -> ChatMessage:
        return super().create_from_dict(db, obj_in=obj_in)

    def get_by_id(self, db: Session, *, message_id: uuid.UUID) -> Optional[ChatMessage]:
        return db.query(self.model).filter(self.model.id == message_id).first()

    def list_by_room_paginated(
        self,
        db: Session,
        *,
        room_id: uuid.UUID,
        page: int = 1,
        limit: int = 50,
        before_id: Optional[uuid.UUID] = None,
    ) -> Tuple[List[ChatMessage], int]:
        """List messages in a room, newest first. Optional before_id for cursor pagination."""
        base = db.query(self.model).filter(self.model.room_id == room_id)
        if before_id:
            msg = self.get_by_id(db, message_id=before_id)
            if msg and msg.room_id == room_id:
                base = base.filter(self.model.created_at < msg.created_at)
        total = base.with_entities(func.count(self.model.id)).scalar() or 0
        skip = (page - 1) * limit if not before_id else 0
        items = (
            base.order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total


chat_message_crud = CRUDChatMessage(ChatMessage)
