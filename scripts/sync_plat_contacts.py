"""
Sync contacts from Plat API (Rails) into the local contacts table.
Run from project root: python -m scripts.sync_plat_contacts
In Docker: set PLAT_API_URL, PLAT_API_TOKEN. PLAT_SYNC_USER_ID optional; else user by PLAT_SYNC_USER_EMAIL (default mair@ifcroofing.com).
"""
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import requests

# Add project root so app imports work
sys.path.insert(0, ".")

from app.core.config import settings
from app.core.database import SessionLocal
from app.crud import contact_crud, user_crud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prefer env (Docker); fallback to settings
PLAT_API_URL = os.environ.get("PLAT_API_URL") or getattr(settings, "PLAT_API_URL", None) or "http://localhost:3000"
PLAT_API_TOKEN = os.environ.get("PLAT_API_TOKEN") or getattr(settings, "PLAT_API_TOKEN", None) or ""
PLAT_SYNC_USER_ID = os.environ.get("PLAT_SYNC_USER_ID") or getattr(settings, "PLAT_SYNC_USER_ID", None) or ""
# When PLAT_SYNC_USER_ID not set, look up user by this email (default: mair@ifcroofing.com)
PLAT_SYNC_USER_EMAIL = os.environ.get("PLAT_SYNC_USER_EMAIL") or getattr(settings, "PLAT_SYNC_USER_EMAIL", None) or "mair@ifcroofing.com"
# When calling Plat from Docker (host.docker.internal), send this Host header so Rails allows the request (default: localhost:3000)
PLAT_API_HOST_HEADER = os.environ.get("PLAT_API_HOST_HEADER") or getattr(settings, "PLAT_API_HOST_HEADER", None) or "localhost:3000"


def fetch_all_plat_contacts(
    base_url: str,
    token: str,
    per_page: int = 100,
    host_header: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch all contacts from Plat API (paginated)."""
    url = f"{base_url.rstrip('/')}/contacts"
    headers = {"Authorization": f"Bearer {token}"}
    if host_header:
        headers["Host"] = host_header
    all_contacts: List[Dict[str, Any]] = []
    page = 1
    while True:
        r = requests.get(
            url,
            params={"page": page, "per_page": per_page},
            headers=headers,
            timeout=30,
        )
        if not r.ok:
            try:
                body = r.text[:500] if r.text else "(empty)"
            except Exception:
                body = "(unreadable)"
            logger.error("Plat API %s %s: %s", r.status_code, r.reason, body)
        r.raise_for_status()
        data = r.json()
        contacts = data.get("contacts") or []
        total_pages = data.get("total_pages", 1)
        all_contacts.extend(contacts)
        logger.info("Plat API page %s/%s: %s contacts", page, total_pages, len(contacts))
        if page >= total_pages or not contacts:
            break
        page += 1
    return all_contacts


def plat_contact_to_our_row(c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map Plat API contact to our Contact table fields. Returns None if email missing."""
    email = (c.get("email") or "").strip()
    if not email:
        return None
    addr = c.get("address") or {}
    return {
        "email": email,
        "name": (c.get("name") or "").strip() or None,
        "phone_number": (c.get("phone_number") or "").strip() or None,
        "address_line1": (addr.get("street_address_1") or "").strip() or None,
        "city": (addr.get("city") or "").strip() or None,
        "state": (addr.get("state") or "").strip() or None,
        "postal_code": (addr.get("zip") or "").strip() or None,
        "country": "US",
    }


def run_sync() -> None:
    import uuid

    if not PLAT_API_TOKEN:
        logger.error("PLAT_API_TOKEN is not set. Set env PLAT_API_TOKEN or PLAT_API_TOKEN in config.")
        sys.exit(1)

    sync_user_id = None
    if PLAT_SYNC_USER_ID:
        try:
            sync_user_id = uuid.UUID(PLAT_SYNC_USER_ID)
        except ValueError:
            logger.error("PLAT_SYNC_USER_ID must be a valid UUID.")
            sys.exit(1)
    else:
        # Look up user by email (default mair@ifcroofing.com)
        db = SessionLocal()
        try:
            user = user_crud.get_by_email(db, PLAT_SYNC_USER_EMAIL)
            if not user:
                logger.error(
                    "User with email %r not found and PLAT_SYNC_USER_ID is not set. "
                    "Create that user or set PLAT_SYNC_USER_ID to a backend user UUID.",
                    PLAT_SYNC_USER_EMAIL,
                )
                sys.exit(1)
            sync_user_id = user.id
            logger.info("PLAT_SYNC_USER_ID not set; using user by email: %s (%s)", sync_user_id, user.email)
        finally:
            db.close()

    logger.info("Fetching contacts from Plat API at %s ...", PLAT_API_URL)
    try:
        plat_contacts = fetch_all_plat_contacts(
            PLAT_API_URL, PLAT_API_TOKEN, host_header=PLAT_API_HOST_HEADER or None
        )
    except requests.RequestException as e:
        logger.exception("Plat API request failed: %s", e)
        sys.exit(1)

    logger.info("Fetched %s contacts. Upserting into DB for user %s.", len(plat_contacts), sync_user_id)
    db = SessionLocal()
    created = updated = skipped = 0
    try:
        for c in plat_contacts:
            row = plat_contact_to_our_row(c)
            if not row:
                skipped += 1
                continue
            existing = contact_crud.get_by_user_and_email(db, user_id=sync_user_id, email=row["email"])
            if existing:
                contact_crud.update(
                    db,
                    db_obj=existing,
                    obj_in={
                        "name": row["name"],
                        "phone_number": row["phone_number"],
                        "address_line1": row["address_line1"],
                        "city": row["city"],
                        "state": row["state"],
                        "postal_code": row["postal_code"],
                        "country": row["country"],
                    },
                )
                updated += 1
            else:
                contact_crud.create_from_dict(
                    db,
                    obj_in={
                        "user_id": sync_user_id,
                        "email": row["email"],
                        "name": row["name"],
                        "phone_number": row["phone_number"],
                        "address_line1": row["address_line1"],
                        "city": row["city"],
                        "state": row["state"],
                        "postal_code": row["postal_code"],
                        "country": row["country"],
                    },
                )
                created += 1
    finally:
        db.close()

    logger.info("Sync done: created=%s, updated=%s, skipped (no email)=%s", created, updated, skipped)


if __name__ == "__main__":
    run_sync()
