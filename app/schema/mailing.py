"""
Mailing schemas.
"""
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel


class MailingCreateBody(BaseModel):
    postcard_id: uuid.UUID
    contact_ids: Optional[List[uuid.UUID]] = None
    recipient_name: Optional[str] = None
    recipient_address: Optional[str] = None
    send_sender_copy: bool = False


class MailingResponse(BaseModel):
    id: uuid.UUID
    postcard_id: uuid.UUID
    user_id: uuid.UUID
    contact_id: Optional[uuid.UUID] = None
    recipient_name: Optional[str] = None
    recipient_address: Optional[str] = None
    status: str
    external_id: Optional[str] = None
    created_at: datetime
    front_artwork: Optional[str] = None
    back_artwork: Optional[str] = None

    class Config:
        from_attributes = True


class MailingCreateResult(BaseModel):
    contact_id: Optional[uuid.UUID] = None
    recipient_name: Optional[str] = None
    mailing_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    success: bool
    error: Optional[str] = None


class MailingCreateResponse(BaseModel):
    message: str = "Mailings submitted"
    results: List[MailingCreateResult]
    sender_copy: Optional[MailingCreateResult] = None
    front_artwork: Optional[str] = None
    back_artwork: Optional[str] = None
