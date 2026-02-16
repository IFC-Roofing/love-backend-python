"""
Mailings API: send postcards via DMM. Trigger send after postcard is created.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import validate_session
from app.core.exceptions import NotFound
from app.crud import contact_crud, mailing_crud, postcard_crud
from app.dmm import build_front_html, build_back_html, dmm_client
from app.dmm.address import normalize_state, parse_address_json
from app.dmm.client import DMMClientError
from app.model.contact import Contact
from app.model.postcard import Postcard
from app.schema.mailing import (
    MailingCreateBody,
    MailingCreateResponse,
    MailingCreateResult,
    MailingResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _contact_to_address(contact: Contact) -> Dict[str, Any]:
    name = (contact.name or "").strip()
    first_name, last_name = name, ""
    if name:
        parts = name.split(None, 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""
    return {
        "first_name": first_name,
        "last_name": last_name,
        "address_line1": (contact.address_line1 or "").strip(),
        "address_city": (contact.city or "").strip(),
        "address_state": normalize_state(contact.state) or "",
        "address_zip": (contact.postal_code or "").strip(),
        "address_country": (contact.country or "US").strip() or "US",
    }


def _parse_recipient_address(recipient_name: Optional[str], recipient_address: Optional[str]) -> Dict[str, Any]:
    name = (recipient_name or "").strip()
    first_name, last_name = name, ""
    if name:
        parts = name.split(None, 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""
    addr = (recipient_address or "").strip()
    lines = [s.strip() for s in addr.split("\n") if s.strip()]
    address_line1 = lines[0] if lines else ""
    city = state = zip_code = ""
    if len(lines) >= 2:
        last = lines[-1]
        if "," in last:
            city_part, rest = last.split(",", 1)
            city = city_part.strip()
            rest = rest.strip().split()
            if rest:
                state = rest[0]
                zip_code = rest[1] if len(rest) >= 2 else ""
        else:
            city = last
    return {
        "first_name": first_name,
        "last_name": last_name,
        "address_line1": address_line1,
        "address_city": city,
        "address_state": normalize_state(state) if state else "",
        "address_zip": zip_code,
        "address_country": "US",
    }


def _build_html_from_postcard(postcard: Postcard) -> tuple:
    front_html = build_front_html(postcard.front_image_path)
    back_html = build_back_html(
        postcard.back_image_path,
        personal_message=postcard.personal_message,
        qr_code_data=postcard.qr_code_data,
    )
    return front_html, back_html


@router.post("", response_model=MailingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_mailings(
    body: MailingCreateBody,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """
    Send postcard via DMM (trigger send). After postcard is created, call this with postcard_id and recipients.
    Use contact_ids (contacts must have address) or recipient_name + recipient_address.
    """
    if not settings.use_dmm:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DMM_NOT_CONFIGURED", "message": "Set DIRECT_MAIL_MANAGER_API_URL and DIRECT_MAIL_MANAGER_API_KEY in .env"},
        )

    user_id = uuid.UUID(current_user["user_id"])
    postcard = postcard_crud.get_by_user_and_id(db, user_id=user_id, postcard_id=body.postcard_id)
    if not postcard:
        raise NotFound("Postcard")

    front_html, back_html = _build_html_from_postcard(postcard)
    from_address = parse_address_json(settings.DMM_FROM_ADDRESS)

    results: List[MailingCreateResult] = []
    recipients: List[tuple] = []

    if body.contact_ids:
        for cid in body.contact_ids:
            contact = contact_crud.get_by_user_and_id(db, user_id=user_id, contact_id=cid)
            if not contact:
                results.append(MailingCreateResult(contact_id=cid, success=False, error="Contact not found or not yours."))
                continue
            if not (contact.address_line1 and contact.city and (contact.state or contact.postal_code)):
                results.append(
                    MailingCreateResult(
                        contact_id=cid,
                        recipient_name=contact.name or contact.email,
                        success=False,
                        error="Contact missing mailing address (address_line1, city, state/postal_code).",
                    )
                )
                continue
            recipients.append((str(contact.id), contact.name or contact.email, _contact_to_address(contact)))
    elif body.recipient_name is not None or body.recipient_address:
        to_addr = _parse_recipient_address(body.recipient_name, body.recipient_address)
        if not to_addr.get("address_line1"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ADDRESS", "message": "recipient_address must contain at least one line."},
            )
        recipients.append((None, body.recipient_name or "Recipient", to_addr))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_RECIPIENTS", "message": "Provide contact_ids or recipient_name + recipient_address."},
        )

    for contact_id_str, rec_name, to_addr in recipients:
        try:
            resp = dmm_client.create_postcard(
                front_html=front_html,
                back_html=back_html,
                to_address=to_addr,
                from_address=from_address,
                name=f"Postcard - {rec_name}",
            )
            external_id = resp.get("id")
            status_val = resp.get("status", "pending")
            contact_uuid = uuid.UUID(contact_id_str) if contact_id_str else None
            obj_in = {
                "postcard_id": body.postcard_id,
                "user_id": user_id,
                "contact_id": contact_uuid,
                "recipient_name": rec_name if not contact_uuid else None,
                "recipient_address": None,
                "status": status_val,
                "external_id": external_id,
            }
            if not contact_uuid and body.recipient_name is not None:
                obj_in["recipient_name"] = body.recipient_name
            if not contact_uuid and body.recipient_address:
                obj_in["recipient_address"] = body.recipient_address
            mailing = mailing_crud.create_from_dict(db, obj_in=obj_in)
            results.append(
                MailingCreateResult(
                    contact_id=contact_uuid,
                    recipient_name=rec_name,
                    mailing_id=mailing.id,
                    external_id=external_id,
                    success=True,
                )
            )
        except DMMClientError as e:
            logger.warning("DMM create postcard failed: %s", e)
            results.append(
                MailingCreateResult(
                    contact_id=uuid.UUID(contact_id_str) if contact_id_str else None,
                    recipient_name=rec_name,
                    success=False,
                    error=str(e),
                )
            )

    sender_copy_result: Optional[MailingCreateResult] = None
    if body.send_sender_copy:
        sender_addr = parse_address_json(settings.DMM_SENDER_COPY_ADDRESS)
        if sender_addr:
            sender_addr = dict(sender_addr)
            sender_addr.setdefault("address_country", "US")
            sender_addr.setdefault("first_name", "")
            sender_addr.setdefault("last_name", "")
            try:
                resp = dmm_client.create_postcard(
                    front_html=front_html,
                    back_html=back_html,
                    to_address=sender_addr,
                    from_address=from_address,
                    name="Postcard - Sender Copy",
                )
                mailing = mailing_crud.create_from_dict(
                    db,
                    obj_in={
                        "postcard_id": body.postcard_id,
                        "user_id": user_id,
                        "contact_id": None,
                        "recipient_name": "Sender copy",
                        "recipient_address": None,
                        "status": resp.get("status", "pending"),
                        "external_id": resp.get("id"),
                    },
                )
                sender_copy_result = MailingCreateResult(
                    mailing_id=mailing.id,
                    external_id=resp.get("id"),
                    success=True,
                    recipient_name="Sender copy",
                )
            except DMMClientError as e:
                sender_copy_result = MailingCreateResult(success=False, error=str(e), recipient_name="Sender copy")

    return MailingCreateResponse(
        message="Mailings submitted",
        results=results,
        sender_copy=sender_copy_result,
        front_artwork=front_html,
        back_artwork=back_html,
    )


def _mailing_to_response(mailing) -> MailingResponse:
    """Build MailingResponse with front_artwork and back_artwork from postcard."""
    data = {
        "id": mailing.id,
        "postcard_id": mailing.postcard_id,
        "user_id": mailing.user_id,
        "contact_id": mailing.contact_id,
        "recipient_name": mailing.recipient_name,
        "recipient_address": mailing.recipient_address,
        "status": mailing.status,
        "external_id": mailing.external_id,
        "created_at": mailing.created_at,
        "front_artwork": None,
        "back_artwork": None,
    }
    if mailing.postcard:
        f, b = _build_html_from_postcard(mailing.postcard)
        data["front_artwork"] = f
        data["back_artwork"] = b
    return MailingResponse(**data)


@router.get("", response_model=List[MailingResponse])
async def list_mailings(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20,
):
    """List mailings for the current user."""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    user_id = uuid.UUID(current_user["user_id"])
    items, _ = mailing_crud.list_by_user_paginated(db, user_id=user_id, page=page, limit=limit)
    return [_mailing_to_response(m) for m in items]


@router.get("/{mailing_id}", response_model=MailingResponse)
async def get_mailing(
    mailing_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """Get a single mailing by id."""
    user_id = uuid.UUID(current_user["user_id"])
    mailing = mailing_crud.get_by_user_and_id(db, user_id=user_id, mailing_id=mailing_id)
    if not mailing:
        raise NotFound("Mailing")
    return _mailing_to_response(mailing)


@router.post("/sync-status", status_code=status.HTTP_200_OK)
async def sync_mailing_status(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """Sync status from DMM for pending mailings."""
    if not settings.use_dmm:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DMM_NOT_CONFIGURED", "message": "DMM is not configured."},
        )
    user_id = uuid.UUID(current_user["user_id"])
    pending = mailing_crud.list_pending_with_external_id(db, user_id=user_id, limit=100)
    updated = 0
    for mailing in pending:
        try:
            info = dmm_client.get_postcard(mailing.external_id)
            new_status = info.get("status") or mailing.status
            if new_status != mailing.status:
                mailing.status = new_status
                db.commit()
                updated += 1
        except DMMClientError:
            pass
    return {"message": "Sync complete", "updated_count": updated}
