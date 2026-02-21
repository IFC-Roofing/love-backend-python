"""
Remove Plat-synced contacts that have incomplete address (address_line1 set but city/state/postal_code null).
Run after fixing sync logic to clean up bad records, then re-run sync_plat_contacts.

Run from project root: python -m scripts.remove_plat_synced_contacts
Uses same user as sync: PLAT_SYNC_USER_ID or PLAT_SYNC_USER_EMAIL (default mair@ifcroofing.com).
"""
import logging
import os
import sys
import uuid

# Add project root so app imports work
sys.path.insert(0, ".")

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.crud import user_crud
from app.model.contact import Contact

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLAT_SYNC_USER_ID = os.environ.get("PLAT_SYNC_USER_ID") or getattr(settings, "PLAT_SYNC_USER_ID", None) or ""
PLAT_SYNC_USER_EMAIL = (
    os.environ.get("PLAT_SYNC_USER_EMAIL")
    or getattr(settings, "PLAT_SYNC_USER_EMAIL", None)
    or "mair@ifcroofing.com"
)


def run_remove() -> None:
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
                logger.error("User with email %r not found. Set PLAT_SYNC_USER_ID or create user.", PLAT_SYNC_USER_EMAIL)
                sys.exit(1)
            sync_user_id = user.id
            logger.info("Using user by email: %s (%s)", sync_user_id, user.email)
        finally:
            db.close()

    db = SessionLocal()
    try:
        # Contacts that have address_line1 but are missing city, state, or postal_code
        q = db.query(Contact).filter(
            Contact.user_id == sync_user_id,
            Contact.address_line1.isnot(None),
            (Contact.address_line1 != ""),
            or_(
                Contact.city.is_(None),
                Contact.state.is_(None),
                Contact.postal_code.is_(None),
            ),
        )
        to_delete = q.all()
        count = len(to_delete)
        if count == 0:
            logger.info("No incomplete-address contacts found for user %s.", sync_user_id)
            return
        for c in to_delete:
            db.delete(c)
        db.commit()
        logger.info("Removed %s contacts with incomplete address (null city/state/postal_code) for user %s.", count, sync_user_id)
    finally:
        db.close()


if __name__ == "__main__":
    run_remove()
