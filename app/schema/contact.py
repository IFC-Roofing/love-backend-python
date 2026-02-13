"""
Contact schemas.
"""
import uuid
from pydantic import BaseModel


class ContactResponse(BaseModel):
    """Contact for list/detail."""
    id: uuid.UUID
    user_id: uuid.UUID
    email: str

    class Config:
        from_attributes = True
