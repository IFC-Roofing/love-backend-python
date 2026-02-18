"""
Chat participant CRUD.
"""
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.orm import Session

from app.model.chat_participant import ChatParticipant
from app.crud.base import CRUDBase


class CRUDChatParticipant(CRUDBase[ChatParticipant, Dict[str, Any], Dict[str, Any]]):
    def create_from_dict(self, db: Session, *, obj_in: Dict[str, Any]) -> ChatParticipant:
        return super().create_from_dict(db, obj_in=obj_in)

    def get_by_room_and_user(
        self, db: Session, *, room_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[ChatParticipant]:
        return (
            db.query(self.model)
            .filter(
                self.model.room_id == room_id,
                self.model.user_id == user_id,
            )
            .first()
        )

    def list_by_room(self, db: Session, *, room_id: uuid.UUID) -> List[ChatParticipant]:
        return db.query(self.model).filter(self.model.room_id == room_id).all()

    def list_other_participants(
        self, db: Session, *, room_id: uuid.UUID, exclude_user_id: uuid.UUID
    ) -> List[ChatParticipant]:
        return (
            db.query(self.model)
            .filter(
                self.model.room_id == room_id,
                self.model.user_id != exclude_user_id,
            )
            .all()
        )

    def mark_read(self, db: Session, *, participant: ChatParticipant) -> None:
        participant.unread_count = 0
        db.add(participant)
        db.commit()

    def increment_unread_for_others(
        self, db: Session, *, room_id: uuid.UUID, exclude_user_id: uuid.UUID
    ) -> None:
        others = self.list_other_participants(
            db, room_id=room_id, exclude_user_id=exclude_user_id
        )
        for p in others:
            p.unread_count = (p.unread_count or 0) + 1
            db.add(p)
        if others:
            db.commit()


chat_participant_crud = CRUDChatParticipant(ChatParticipant)
