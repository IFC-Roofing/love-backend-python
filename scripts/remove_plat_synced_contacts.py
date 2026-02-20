"""
Remove contacts that were added/updated by the Plat sync (sync_plat_contacts.py),
so the DB is back to the state before that script ran.

Keeps only the original seed contacts (from migrations) for the sync user;
deletes all other contacts for that user (i.e. those that came from Plat API).

Run from project root: python -m scripts.remove_plat_synced_contacts  (or: python scripts/remove_plat_synced_contacts.py)
In Docker: same env as sync (PLAT_SYNC_USER_EMAIL or PLAT_SYNC_USER_ID).
"""
import logging
import os
import sys

# Add project root so app imports work
sys.path.insert(0, ".")

from app.core.config import settings
from app.core.database import SessionLocal
from app.crud import contact_crud, user_crud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLAT_SYNC_USER_ID = os.environ.get("PLAT_SYNC_USER_ID") or getattr(settings, "PLAT_SYNC_USER_ID", None) or ""
PLAT_SYNC_USER_EMAIL = os.environ.get("PLAT_SYNC_USER_EMAIL") or getattr(settings, "PLAT_SYNC_USER_EMAIL", None) or "mair@ifcroofing.com"

# Original seed contact emails (from migrations). Only these are kept for the sync user.
SEED_EMAILS = {
    "jhowittpitt@hotmail.com",
    "jamie.moilanen@gmail.com",
    "dawson.mona@yahoo.com",
    "sheryl@ifcroofing.com",
    "alice@example.com",
    "bob.smith@test.org",
    "carol.jones@gmail.com",
}


def run_remove() -> None:
    import uuid

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
                    "User with email %r not found. Set PLAT_SYNC_USER_ID or PLAT_SYNC_USER_EMAIL.",
                    PLAT_SYNC_USER_EMAIL,
                )
                sys.exit(1)
            sync_user_id = user.id
            logger.info("Using user by email: %s (%s)", sync_user_id, user.email)
        finally:
            db.close()

    db = SessionLocal()
    try:
        contacts = contact_crud.list_by_user(db, user_id=sync_user_id)
        to_delete = [c for c in contacts if c.email not in SEED_EMAILS]
        if not to_delete:
            logger.info("No Plat-synced contacts to remove for user %s.", sync_user_id)
            return
        logger.info("Removing %s contacts (keeping %s seed contacts) for user %s.", len(to_delete), len(contacts) - len(to_delete), sync_user_id)
        for c in to_delete:
            contact_crud.delete(db, id=c.id)
        logger.info("Done. Removed %s contacts. Remaining for this user: %s.", len(to_delete), len(contacts) - len(to_delete))
    finally:
        db.close()


if __name__ == "__main__":
    run_remove()
