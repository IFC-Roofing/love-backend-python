"""
Contacts API: list current user's contacts with pagination and optional search.
"""
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import validate_session
from app.core.exceptions import NotFound
from app.crud import contact_crud
from app.schema.contact import ContactListResponse, ContactResponse

router = APIRouter()

DEFAULT_LIMIT = 100
MAX_LIMIT = 100


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
    limit: int = Query(
        DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Number of contacts per page (1–100). Default 100.",
    ),
    offset: int = Query(0, ge=0, description="Number of contacts to skip. Default 0."),
    search: Optional[str] = Query(
        None,
        description="Search in name or email (case-insensitive, partial match).",
    ),
    name: Optional[str] = Query(
        None,
        description="Filter by name (case-insensitive, partial match).",
    ),
    email: Optional[str] = Query(
        None,
        description="Filter by email (case-insensitive, partial match).",
    ),
):
    """
    List contacts for the current user with pagination.
    Optional query params: limit (1–100, default 100), offset (default 0),
    search (matches name or email), name, email (filters).
    Requires Bearer token.
    """
    user_id = uuid.UUID(current_user["user_id"])
    contacts, total = contact_crud.list_by_user_paginated(
        db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        search=search,
        name=name,
        email=email,
    )
    return ContactListResponse(
        contacts=[ContactResponse.model_validate(c) for c in contacts],
        total=total,
        limit=limit,
        offset=offset,
    )


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
    return ContactResponse.model_validate(contact)
