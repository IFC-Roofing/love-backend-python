"""Seed all contacts for every user (idempotent, prod-safe)

Run after all schema migrations. Ensures every existing user has the full set of
seed contacts. Safe to run on empty or already-seeded DB; skips existing rows.

Revision ID: j01234567890
Revises: i90123456789
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "j01234567890"
down_revision: Union[str, None] = "i90123456789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Full set of seed contacts for every user (prod + dev). Insert only if missing per (user_id, email).
SEED_CONTACTS = [
    {
        "name": "Jennifer Jaeger",
        "email": "jhowittpitt@hotmail.com",
        "phone_number": "8172295162",
        "address_line1": "2504 Springhill Dr",
        "city": "Grapevine",
        "state": "TX",
        "postal_code": "76051",
        "country": "US",
    },
    {
        "name": "Jamie Moilanen",
        "email": "jamie.moilanen@gmail.com",
        "phone_number": "8175059530",
        "address_line1": "2205 Forest Oak Ct",
        "city": "Bedford",
        "state": "TX",
        "postal_code": "76021",
        "country": "US",
    },
    {
        "name": "Mona Dawson",
        "email": "dawson.mona@yahoo.com",
        "phone_number": "8172023385",
        "address_line1": "3418 Sprindeltree Dr",
        "city": "Grapevine",
        "state": "TX",
        "postal_code": "76051",
        "country": "US",
    },
    {
        "name": "Sheryl May",
        "email": "sheryl@ifcroofing.com",
        "phone_number": None,
        "address_line1": "5115 Colleyville Boulevard",
        "city": "Colleyville",
        "state": "TX",
        "postal_code": "76034",
        "country": "US",
    },
]


def _get_all_user_ids(conn) -> list:
    """Return list of user id strings (UUIDs) for every user in users table."""
    r = conn.execute(text("SELECT id FROM users"))
    return [str(row[0]) for row in r.fetchall()]


def _contact_exists(conn, user_id: str, email: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM contacts WHERE user_id = :uid AND email = :email LIMIT 1"),
        {"uid": user_id, "email": email},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    for uid in _get_all_user_ids(conn):
        for c in SEED_CONTACTS:
            if _contact_exists(conn, uid, c["email"]):
                continue
            conn.execute(
                text("""
                    INSERT INTO contacts (id, user_id, email, phone_number, name, address_line1, city, state, postal_code, country)
                    VALUES (gen_random_uuid(), :uid, :email, :phone_number, :name, :address_line1, :city, :state, :postal_code, :country)
                """),
                {
                    "uid": uid,
                    "email": c["email"],
                    "phone_number": c["phone_number"],
                    "name": c["name"],
                    "address_line1": c["address_line1"],
                    "city": c["city"],
                    "state": c["state"],
                    "postal_code": c["postal_code"],
                    "country": c["country"],
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    for c in SEED_CONTACTS:
        conn.execute(text("DELETE FROM contacts WHERE email = :email"), {"email": c["email"]})
