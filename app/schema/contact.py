"""
Contact schemas.
"""
import uuid
from typing import Optional
from pydantic import BaseModel


class ContactResponse(BaseModel):
    """Contact for list/detail."""
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    phone_number: Optional[str] = None
    name: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    class Config:
        from_attributes = True
