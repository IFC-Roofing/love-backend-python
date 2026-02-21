"""
Sync contacts from Plat GraphQL API into the local contacts table.
Run from project root: python -m scripts.sync_plat_contacts
Set PLAT_GRAPHQL_URL (default https://omni.ifc.shibui.ar/graphql), PLAT_API_TOKEN.
PLAT_SYNC_USER_ID optional; else user by PLAT_SYNC_USER_EMAIL (default mair@ifcroofing.com).

Only imports contacts with complete information: name, email, and fullAddress required;
phone can be missing. Skips if the current user already has a contact with the same name.
"""
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

# Add project root so app imports work
sys.path.insert(0, ".")

from app.core.config import settings
from app.core.database import SessionLocal
from app.crud import contact_crud, user_crud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GraphQL endpoint (POST)
PLAT_GRAPHQL_URL = (
    os.environ.get("PLAT_GRAPHQL_URL")
    or getattr(settings, "PLAT_GRAPHQL_URL", None)
    or "https://omni.ifc.shibui.ar/graphql"
)
PLAT_API_TOKEN = os.environ.get("PLAT_API_TOKEN") or getattr(settings, "PLAT_API_TOKEN", None) or ""
PLAT_SYNC_USER_ID = os.environ.get("PLAT_SYNC_USER_ID") or getattr(settings, "PLAT_SYNC_USER_ID", None) or ""
PLAT_SYNC_USER_EMAIL = (
    os.environ.get("PLAT_SYNC_USER_EMAIL")
    or getattr(settings, "PLAT_SYNC_USER_EMAIL", None)
    or "mair@ifcroofing.com"
)
PER_PAGE = 50


def fetch_all_plat_contacts(graphql_url: str, token: str, per_page: int = 50) -> List[Dict[str, Any]]:
    """Fetch all contacts from Plat GraphQL API (paginated). POST with contacts query."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    all_contacts: List[Dict[str, Any]] = []
    page = 1
    while True:
        query = (
            "query { contacts(page: %d, perPage: %d) { contacts { id name email phoneNumber fullAddress statusName } totalPages } }"
            % (page, per_page)
        )
        payload = {"query": query}
        r = requests.post(graphql_url, json=payload, headers=headers, timeout=30)
        if not r.ok:
            try:
                body = r.text[:500] if r.text else "(empty)"
            except Exception:
                body = "(unreadable)"
            logger.error("Plat GraphQL %s %s: %s", r.status_code, r.reason, body)
            r.raise_for_status()
        data = r.json()
        if "data" not in data or "contacts" not in data["data"]:
            errors = data.get("errors", [])
            logger.error("GraphQL errors: %s", errors)
            raise ValueError("GraphQL response missing data.contacts: %s" % (errors or data))
        conn = data["data"]["contacts"]
        contacts = conn.get("contacts") or []
        try:
            total_pages = int(conn.get("totalPages") or 1)
        except (TypeError, ValueError):
            total_pages = 1
        all_contacts.extend(contacts)
        logger.info("Plat GraphQL page %s/%s: %s contacts", page, total_pages, len(contacts))
        if page >= total_pages or not contacts:
            break
        page += 1
    return all_contacts


# Match US state (2 letters) and ZIP (5 or 5+4 digits)
_RE_STATE = re.compile(r"^[A-Za-z]{2}$")
_RE_ZIP = re.compile(r"^\d{5}(?:-\d{4})?$")

# Full state name -> 2-letter code (for addresses like "Fort Worth, Texas, 76137")
_STATE_FULL_TO_ABBR: Dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}


def _normalize_state(raw: str) -> Optional[str]:
    """Return 2-letter state code; accept 2-letter or full name (e.g. Texas -> TX)."""
    if not raw:
        return None
    s = raw.strip()
    if _RE_STATE.match(s):
        return s.upper()
    return _STATE_FULL_TO_ABBR.get(s.lower())


def _parse_single_line_parts(parts: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Parse comma-separated parts into (address_line1, city, state, postal_code). Returns (None, None, None, None) if not parseable."""
    if not parts:
        return None, None, None, None
    # Normalize: strip each part (API may return trailing/leading whitespace or odd chars)
    parts = [p.strip() for p in parts]
    last = parts[-1].strip() if parts else ""
    # Accept ZIP with optional trailing .0 (e.g. 75013.0 from JSON number)
    if last and last.endswith(".0") and last[:-2].isdigit():
        last = last[:-2]
    if not _RE_ZIP.match(last):
        return None, None, None, None
    postal_code = last
    state = _normalize_state(parts[-2]) if len(parts) >= 2 else None
    if not state:
        return None, None, None, None
    if len(parts) >= 5:
        # "Street, City ZIP, City, ST, ZIP" (e.g. 670 Jernigan Rd, Lewisville 75077, Lewisville, TX, 75077)
        address_line1 = parts[0]
        city = parts[2]  # clean city name (no zip)
        return address_line1, city, state, postal_code
    if len(parts) >= 4:
        # "Street, City, ST, ZIP" or "Street, City, Texas, ZIP"
        city = parts[-3]
        address_line1 = ", ".join(parts[:-3])
        return address_line1, city, state, postal_code
    if len(parts) == 3:
        # "Street, City, ST 12345"
        address_line1 = parts[0]
        city = parts[1]
        return address_line1, city, state, postal_code
    return None, None, None, None


def parse_full_address(full_address: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse fullAddress string into (address_line1, city, state, postal_code).
    Handles: "Street, City, ST, ZIP" (4 parts); "Street, City ZIP, City, ST, ZIP" (5 parts);
    "Street, City, Texas, ZIP" (full state name); "Street, City, ST 12345" (3 parts); or newline-separated.
    """
    addr = (full_address or "").strip()
    if not addr:
        return None, None, None, None
    lines = [s.strip() for s in addr.replace("\r", "\n").split("\n") if s.strip()]
    if not lines:
        return None, None, None, None

    def _parse_one_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        parts = [p.strip() for p in line.split(",")]
        address_line1, city, state, postal_code = _parse_single_line_parts(parts)
        if address_line1 is not None:
            return address_line1, city, state, postal_code
        if len(parts) >= 3:
            last = parts[-1].strip()
            match = re.match(r"^([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)$", last)
            if match:
                return parts[0], parts[1], match.group(1), match.group(2)
        return None, None, None, None

    if len(lines) == 1:
        # Single line: "927 Pelican Dr, Allen, TX, 75013" – parse as comma-separated
        return _parse_one_line(lines[0])

    # Multiline: first line = street, last line = city, state, zip
    address_line1 = lines[0]
    city = state = postal_code = None
    last = lines[-1]
    parts = [p.strip() for p in last.split(",")]
    address_line1_parsed, city, state, postal_code = _parse_single_line_parts(parts)
    if address_line1_parsed is not None:
        return (lines[0], city, state, postal_code)
    if "," in last:
        city_part, rest = last.split(",", 1)
        city = city_part.strip()
        rest = rest.strip()
        match = re.match(r"^([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)$", rest)
        if match:
            state, postal_code = match.group(1), match.group(2)
    else:
        city = last
    return address_line1, city, state, postal_code


def plat_contact_to_our_row(c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Map Plat GraphQL contact to our Contact table fields.
    Requires name, email, and fullAddress (phone optional).
    Returns None if incomplete (missing name, email, or address).
    """
    name = (c.get("name") or "").strip()
    email = (c.get("email") or "").strip()
    full_address = (c.get("fullAddress") or "").strip()
    if not name or not email or not full_address:
        return None
    address_line1, city, state, postal_code = parse_full_address(full_address)
    if not address_line1:
        return None
    # Require at least one of city/state/postal_code so we don't store incomplete addresses
    if not (city or state or postal_code):
        return None
    return {
        "email": email,
        "name": name or None,
        "phone_number": (c.get("phoneNumber") or "").strip() or None,
        "address_line1": address_line1,
        "city": city,
        "state": state,
        "postal_code": postal_code,
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

    logger.info("Fetching contacts from Plat GraphQL at %s ...", PLAT_GRAPHQL_URL)
    try:
        plat_contacts = fetch_all_plat_contacts(PLAT_GRAPHQL_URL, PLAT_API_TOKEN, per_page=PER_PAGE)
    except (requests.RequestException, ValueError) as e:
        logger.exception("Plat GraphQL request failed: %s", e)
        sys.exit(1)

    logger.info("Fetched %s contacts. Syncing into DB for user %s.", len(plat_contacts), sync_user_id)
    db = SessionLocal()
    created = updated = skipped_incomplete = skipped_same_name = 0
    SAMPLE_INCOMPLETE_MAX = 50
    sample_incomplete: List[Dict[str, Any]] = []
    try:
        for c in plat_contacts:
            row = plat_contact_to_our_row(c)
            if not row:
                skipped_incomplete += 1
                if len(sample_incomplete) < SAMPLE_INCOMPLETE_MAX:
                    sample_incomplete.append({
                        "name": (c.get("name") or "").strip()[:80],
                        "email": (c.get("email") or "").strip()[:80],
                        "fullAddress": (c.get("fullAddress") or "").strip()[:200],
                    })
                continue
            existing_by_name = contact_crud.get_by_user_and_name(db, user_id=sync_user_id, name=row["name"])
            if existing_by_name:
                skipped_same_name += 1
                continue
            existing_by_email = contact_crud.get_by_user_and_email(db, user_id=sync_user_id, email=row["email"])
            if existing_by_email:
                contact_crud.update(
                    db,
                    db_obj=existing_by_email,
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

    logger.info(
        "Sync done: created=%s, updated=%s, skipped (incomplete)=%s, skipped (same name)=%s",
        created,
        updated,
        skipped_incomplete,
        skipped_same_name,
    )
    if sample_incomplete:
        logger.info("Sample of skipped (incomplete) contacts (max %s):", SAMPLE_INCOMPLETE_MAX)
        for i, s in enumerate(sample_incomplete, 1):
            logger.info(
                "  [%s] name=%r email=%r fullAddress=%r",
                i,
                s["name"] or "(empty)",
                s["email"] or "(empty)",
                s["fullAddress"] or "(empty)",
            )


if __name__ == "__main__":
    run_sync()
