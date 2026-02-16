"""
Contacts API: list current user's contacts.
"""
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import validate_session
from app.core.exceptions import NotFound
from app.crud import contact_crud
from app.schema.contact import ContactResponse

router = APIRouter()


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """List all contacts for the current user. Requires Bearer token."""
    user_id = uuid.UUID(current_user["user_id"])
    contacts = contact_crud.list_by_user(db, user_id=user_id)
    return [ContactResponse.model_validate(c) for c in contacts]


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """Get a single contact by id (must belong to current user). Requires Bearer token."""
    user_id = uuid.UUID(current_user["user_id"])
    contact = contact_crud.get_by_user_and_id(db, user_id=user_id, contact_id=contact_id)
    if not contact:
        raise NotFound("Contact")
    return contact
