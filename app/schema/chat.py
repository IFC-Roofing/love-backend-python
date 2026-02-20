"""
Chat schemas: rooms and messages.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


# --- Room ---


class LinkedContactDetail(BaseModel):
    """Contact details when room is linked to a contact (contact_id set)."""
    id: uuid.UUID
    name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None  # Optional; Contact model has no image field yet

    class Config:
        from_attributes = True


class RoomCreateBody(BaseModel):
    """Body for POST /chat/rooms (create or get direct room)."""
    other_user_id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None


class RoomResponse(BaseModel):
    """Single room for GET room."""
    id: uuid.UUID
    chat_type: str
    contact_id: Optional[uuid.UUID] = None
    topic: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    unread_count: Optional[int] = None
    other_participants: Optional[List[Dict[str, Any]]] = None
    linked_contact: Optional["LinkedContactDetail"] = None

    class Config:
        from_attributes = True


class LastMessagePreview(BaseModel):
    """Last message snippet for room list."""
    id: uuid.UUID
    content: str
    user_id: uuid.UUID
    created_at: datetime


class RoomListItem(BaseModel):
    """Room in list with unread and last message preview."""
    id: uuid.UUID
    chat_type: str
    contact_id: Optional[uuid.UUID] = None
    topic: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    unread_count: int = 0
    last_message_preview: Optional[LastMessagePreview] = None
    other_participants: Optional[List[Dict[str, Any]]] = None
    linked_contact: Optional["LinkedContactDetail"] = None

    class Config:
        from_attributes = True


class RoomListResponse(BaseModel):
    """Paginated room list."""
    items: List[RoomListItem]
    page: int = Field(..., description="Current page (1-based).")
    limit: int = Field(..., description="Items per page.")
    total: int = Field(..., description="Total rooms for this user.")
    total_pages: int = Field(..., description="Total pages.")


# --- Message ---

class MessageCreateBody(BaseModel):
    """Body for POST /chat/rooms/{room_id}/messages."""
    content: str = Field(..., min_length=1, max_length=10_000)
    quote_id: Optional[uuid.UUID] = None


class MessageResponse(BaseModel):
    """Single message."""
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    quote_id: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Paginated messages for a room."""
    items: List[MessageResponse]
    page: int = Field(..., description="Current page (1-based).")
    limit: int = Field(..., description="Items per page.")
    total: int = Field(..., description="Total messages in room.")
    total_pages: int = Field(..., description="Total pages.")
