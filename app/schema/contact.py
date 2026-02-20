"""
Contact schemas.
"""
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


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


class ContactListResponse(BaseModel):
    """Paginated list of contacts with metadata."""
    contacts: List[ContactResponse]
    total: int = Field(..., description="Total number of contacts matching the filters")
    limit: int = Field(..., description="Page size (limit)")
    offset: int = Field(..., description="Number of contacts skipped")
