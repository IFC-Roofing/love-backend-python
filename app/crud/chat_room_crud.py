"""
Chat room CRUD.
"""
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.model.chat_room import ChatRoom
from app.model.chat_participant import ChatParticipant
from app.crud.base import CRUDBase


class CRUDChatRoom(CRUDBase[ChatRoom, Dict[str, Any], Dict[str, Any]]):
    def create_from_dict(self, db: Session, *, obj_in: Dict[str, Any]) -> ChatRoom:
        return super().create_from_dict(db, obj_in=obj_in)

    def get_by_id(self, db: Session, *, room_id: uuid.UUID) -> Optional[ChatRoom]:
        return db.query(self.model).filter(self.model.id == room_id).first()

    def list_rooms_for_user(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        chat_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[ChatRoom], int]:
        """List rooms the user participates in, ordered by last_message_at desc."""
        subq = (
            db.query(ChatParticipant.room_id)
            .filter(ChatParticipant.user_id == user_id)
        )
        base = db.query(self.model).filter(self.model.id.in_(subq))
        if chat_type:
            base = base.filter(self.model.chat_type == chat_type)
        total = base.with_entities(func.count(self.model.id)).scalar() or 0
        skip = (page - 1) * limit
        # Order by last_message_at desc (nulls last in PostgreSQL), then created_at
        items = (
            base.order_by(
                desc(self.model.last_message_at),
                desc(self.model.created_at),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total


chat_room_crud = CRUDChatRoom(ChatRoom)
