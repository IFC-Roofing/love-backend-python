"""
Chat API: rooms and messages (REST). WebSocket in same module.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db, SessionLocal
from app.core.dependencies import validate_session
from app.core.exceptions import NotFound
from app.crud import (
    chat_room_crud,
    chat_participant_crud,
    chat_message_crud,
    contact_crud,
)
from app.model.chat_message import ChatMessage
from app.model.chat_participant import ChatParticipant
from app.model.chat_room import ChatRoom
from app.model.user import User
from app.schema.chat import (
    LastMessagePreview,
    LinkedContactDetail,
    MessageCreateBody,
    MessageListResponse,
    MessageResponse,
    RoomCreateBody,
    RoomListItem,
    RoomListResponse,
    RoomResponse,
)
from app.chat.connection_manager import connection_manager

router = APIRouter()
logger = logging.getLogger(__name__)


def _message_to_payload(msg: ChatMessage) -> Dict[str, Any]:
    """Serialize message for response and WebSocket broadcast."""
    return {
        "id": str(msg.id),
        "room_id": str(msg.room_id),
        "user_id": str(msg.user_id),
        "content": msg.content,
        "quote_id": str(msg.quote_id) if msg.quote_id else None,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def _other_participants_summary(db: Session, room_id: uuid.UUID, exclude_user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """List of { user_id, email } for participants other than exclude_user_id."""
    others = chat_participant_crud.list_other_participants(
        db, room_id=room_id, exclude_user_id=exclude_user_id
    )
    return [
        {"user_id": str(p.user_id), "email": p.user.email if p.user else None}
        for p in others
    ]


def _linked_contact_for_room(
    db: Session, room: ChatRoom, user_id: uuid.UUID
) -> Optional[LinkedContactDetail]:
    """Build LinkedContactDetail when room has contact_id; else None."""
    if not room.contact_id:
        return None
    contact = contact_crud.get_by_user_and_id(
        db, user_id=user_id, contact_id=room.contact_id
    )
    if not contact:
        return None
    return LinkedContactDetail(
        id=contact.id,
        name=contact.name,
        email=contact.email,
        phone_number=contact.phone_number,
        profile_image_url=getattr(contact, "profile_image_url", None),
    )


# --- REST: Rooms ---

@router.get("/rooms", response_model=RoomListResponse)
async def list_rooms(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20,
    chat_type: Optional[str] = None,
):
    """List rooms the current user participates in."""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    user_id = uuid.UUID(current_user["user_id"])
    rooms, total = chat_room_crud.list_rooms_for_user(
        db, user_id=user_id, chat_type=chat_type, page=page, limit=limit
    )
    items: List[RoomListItem] = []
    for room in rooms:
        part = chat_participant_crud.get_by_room_and_user(
            db, room_id=room.id, user_id=user_id
        )
        unread = part.unread_count if part else 0
        last_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.room_id == room.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
            .first()
        )
        preview = None
        if last_msg:
            preview = LastMessagePreview(
                id=last_msg.id,
                content=last_msg.content[:200] + ("..." if len(last_msg.content) > 200 else ""),
                user_id=last_msg.user_id,
                created_at=last_msg.created_at,
            )
        items.append(
            RoomListItem(
                id=room.id,
                chat_type=room.chat_type,
                contact_id=room.contact_id,
                topic=room.topic,
                last_message_at=room.last_message_at,
                created_at=room.created_at,
                unread_count=unread,
                last_message_preview=preview,
                other_participants=_other_participants_summary(db, room.id, user_id),
                linked_contact=_linked_contact_for_room(db, room, user_id),
            )
        )
    total_pages = (total + limit - 1) // limit if total else 0
    return RoomListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
    )


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_room(
    body: RoomCreateBody,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """Create or get a direct room (by other_user_id or contact_id)."""
    user_id = uuid.UUID(current_user["user_id"])
    if body.other_user_id:
        # Find existing room that has exactly [user_id, other_user_id] as participants
        other_id = body.other_user_id
        if other_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_OTHER_USER", "message": "other_user_id cannot be yourself."},
            )
        # Check other user exists (optional: could skip)
        other_user = db.query(User).filter(User.id == other_id).first()
        if not other_user:
            raise NotFound("User")
        # Find room where both are participants
        my_participations = (
            db.query(ChatParticipant.room_id)
            .filter(ChatParticipant.user_id == user_id)
            .all()
        )
        my_room_ids = [p[0] for p in my_participations]
        for rid in my_room_ids:
            room = chat_room_crud.get_by_id(db, room_id=rid)
            if not room or room.chat_type != "direct":
                continue
            participants = chat_participant_crud.list_by_room(db, room_id=rid)
            user_ids = {p.user_id for p in participants}
            if user_ids == {user_id, other_id}:
                part = chat_participant_crud.get_by_room_and_user(db, room_id=rid, user_id=user_id)
                return RoomResponse(
                    id=room.id,
                    chat_type=room.chat_type,
                    contact_id=room.contact_id,
                    topic=room.topic,
                    last_message_at=room.last_message_at,
                    created_at=room.created_at,
                    unread_count=part.unread_count if part else 0,
                    other_participants=_other_participants_summary(db, room.id, user_id),
                    linked_contact=_linked_contact_for_room(db, room, user_id),
                )
        # Create new room with two participants
        room = chat_room_crud.create_from_dict(
            db,
            obj_in={"id": uuid.uuid4(), "chat_type": "direct"},
        )
        chat_participant_crud.create_from_dict(
            db,
            obj_in={"room_id": room.id, "user_id": user_id},
        )
        chat_participant_crud.create_from_dict(
            db,
            obj_in={"room_id": room.id, "user_id": other_id},
        )
        return RoomResponse(
            id=room.id,
            chat_type=room.chat_type,
            contact_id=room.contact_id,
            topic=room.topic,
            last_message_at=room.last_message_at,
            created_at=room.created_at,
            unread_count=0,
            other_participants=_other_participants_summary(db, room.id, user_id),
            linked_contact=_linked_contact_for_room(db, room, user_id),
        )
    if body.contact_id:
        contact = contact_crud.get_by_user_and_id(db, user_id=user_id, contact_id=body.contact_id)
        if not contact:
            raise NotFound("Contact")
        # Find existing room for this user + contact
        my_participations = (
            db.query(ChatParticipant.room_id)
            .filter(ChatParticipant.user_id == user_id)
            .all()
        )
        for (rid,) in my_participations:
            room = chat_room_crud.get_by_id(db, room_id=rid)
            if room and room.contact_id == body.contact_id:
                part = chat_participant_crud.get_by_room_and_user(db, room_id=rid, user_id=user_id)
                return RoomResponse(
                    id=room.id,
                    chat_type=room.chat_type,
                    contact_id=room.contact_id,
                    topic=room.topic,
                    last_message_at=room.last_message_at,
                    created_at=room.created_at,
                    unread_count=part.unread_count if part else 0,
                    other_participants=[],
                    linked_contact=_linked_contact_for_room(db, room, user_id),
                )
        room = chat_room_crud.create_from_dict(
            db,
            obj_in={"id": uuid.uuid4(), "chat_type": "direct", "contact_id": body.contact_id},
        )
        chat_participant_crud.create_from_dict(
            db,
            obj_in={"room_id": room.id, "user_id": user_id},
        )
        return RoomResponse(
            id=room.id,
            chat_type=room.chat_type,
            contact_id=room.contact_id,
            topic=room.topic,
            last_message_at=room.last_message_at,
            created_at=room.created_at,
            unread_count=0,
            other_participants=[],
            linked_contact=_linked_contact_for_room(db, room, user_id),
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "MISSING_PARAM", "message": "Provide other_user_id or contact_id."},
    )


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """Get one room (only if current user is participant)."""
    user_id = uuid.UUID(current_user["user_id"])
    part = chat_participant_crud.get_by_room_and_user(db, room_id=room_id, user_id=user_id)
    if not part:
        raise NotFound("Room")
    room = chat_room_crud.get_by_id(db, room_id=room_id)
    if not room:
        raise NotFound("Room")
    return RoomResponse(
        id=room.id,
        chat_type=room.chat_type,
        contact_id=room.contact_id,
        topic=room.topic,
        last_message_at=room.last_message_at,
        created_at=room.created_at,
        unread_count=part.unread_count,
        other_participants=_other_participants_summary(db, room.id, user_id),
        linked_contact=_linked_contact_for_room(db, room, user_id),
    )


# --- REST: Messages ---

@router.get("/rooms/{room_id}/messages", response_model=MessageListResponse)
async def list_messages(
    room_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 50,
    before_id: Optional[uuid.UUID] = None,
):
    """Paginated messages for a room. Marks room as read for current user."""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 50
    user_id = uuid.UUID(current_user["user_id"])
    part = chat_participant_crud.get_by_room_and_user(db, room_id=room_id, user_id=user_id)
    if not part:
        raise NotFound("Room")
    chat_participant_crud.mark_read(db, participant=part)
    items, total = chat_message_crud.list_by_room_paginated(
        db, room_id=room_id, page=page, limit=limit, before_id=before_id
    )
    total_pages = (total + limit - 1) // limit if total else 0
    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in items],
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
    )


@router.post("/rooms/{room_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    room_id: uuid.UUID,
    body: MessageCreateBody,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """Create a message. Updates last_message_at, unread for others, and broadcasts to WebSocket subscribers."""
    user_id = uuid.UUID(current_user["user_id"])
    part = chat_participant_crud.get_by_room_and_user(db, room_id=room_id, user_id=user_id)
    if not part:
        raise NotFound("Room")
    room = chat_room_crud.get_by_id(db, room_id=room_id)
    if not room:
        raise NotFound("Room")
    content = body.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_CONTENT", "message": "Message content cannot be empty or whitespace only."},
        )
    if body.quote_id:
        quoted = chat_message_crud.get_by_id(db, message_id=body.quote_id)
        if not quoted or quoted.room_id != room_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_QUOTE", "message": "Quoted message must exist and belong to this room."},
            )
    from datetime import datetime, timezone
    from sqlalchemy.exc import SQLAlchemyError
    try:
        msg = chat_message_crud.create_from_dict(
            db,
            obj_in={
                "room_id": room_id,
                "user_id": user_id,
                "content": content,
                "quote_id": body.quote_id,
            },
        )
        room.last_message_at = datetime.now(timezone.utc)
        db.add(room)
        chat_participant_crud.increment_unread_for_others(db, room_id=room_id, exclude_user_id=user_id)
        db.commit()
        db.refresh(msg)
        db.refresh(room)
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Failed to save chat message: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_ERROR", "message": "Failed to save message. Please try again."},
        )
    payload = _message_to_payload(msg)
    connection_manager.broadcast_to_room_sync(room_id, "message_created", payload)
    return MessageResponse.model_validate(msg)


# --- WebSocket ---

@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """WebSocket for real-time: subscribe to rooms, receive message_created and user_typing. Auth via query ?token=."""
    await websocket.accept()
    user_id = None
    if token:
        from app.session import get_session
        session = get_session(token)
        if session:
            user_id = session.get("user_id")
    if not user_id:
        await websocket.close(code=4001)
        return
    user_id = uuid.UUID(user_id)
    async def send_error(code: str, message: str) -> None:
        try:
            await websocket.send_text(
                json.dumps({"event": "error", "code": code, "message": message})
            )
        except Exception:
            pass

    subscribed: set = set()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                await send_error("INVALID_JSON", "Request body must be valid JSON.")
                continue
            action = obj.get("action")
            room_id_str = obj.get("room_id")
            if not room_id_str:
                await send_error("MISSING_ROOM_ID", "Missing required field: room_id.")
                continue
            try:
                room_id = uuid.UUID(room_id_str)
            except (ValueError, TypeError):
                await send_error("INVALID_ROOM_ID", "room_id must be a valid UUID.")
                continue
            db = SessionLocal()
            try:
                part = chat_participant_crud.get_by_room_and_user(
                    db, room_id=room_id, user_id=user_id
                )
            finally:
                db.close()
            if not part:
                await send_error("FORBIDDEN", "You are not a participant of this room.")
                continue
            if action == "subscribe":
                await connection_manager.subscribe(websocket, room_id)
                subscribed.add(room_id)
            elif action == "unsubscribe":
                await connection_manager.unsubscribe(websocket, room_id)
                subscribed.discard(room_id)
            elif action == "typing":
                typing = obj.get("typing", False)
                await connection_manager.broadcast_to_room(
                    room_id,
                    "user_typing",
                    {"user_id": str(user_id), "typing": typing},
                    exclude_websocket=websocket,
                )
            else:
                await send_error(
                    "UNKNOWN_ACTION",
                    "Expected action: subscribe, unsubscribe, or typing.",
                )
    except Exception as e:
        logger.warning("WebSocket closed: %s", e)
    finally:
        await connection_manager.unsubscribe_all(websocket, subscribed)
