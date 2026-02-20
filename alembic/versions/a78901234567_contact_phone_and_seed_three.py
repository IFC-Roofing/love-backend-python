"""add contact phone_number and seed three contacts for user

Revision ID: a78901234567
Revises: f67890123456
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "a78901234567"
down_revision: Union[str, None] = "f67890123456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_USER_ID = "df8e2c7d-0225-4ac0-b9c9-65cf422860f3"

# Three contacts for the seed user (street_address_1 -> address_line1, country = US)
CONTACTS = [
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
]


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"),
        {"t": table, "c": column},
    )
    return r.scalar() is not None


def _contact_exists(conn, user_id: str, email: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM contacts WHERE user_id = :uid AND email = :email LIMIT 1"),
        {"uid": user_id, "email": email},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "contacts", "phone_number"):
        op.add_column("contacts", sa.Column("phone_number", sa.String(), nullable=True))

    # Seed these contacts for every current user (works in prod: all existing users get the contacts)
    user_ids = _get_all_user_ids(conn)
    for uid in user_ids:
        for c in CONTACTS:
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
    # Remove seed contacts by email (removes from all users)
    for c in CONTACTS:
        conn.execute(
            text("DELETE FROM contacts WHERE email = :email"),
            {"email": c["email"]},
        )
    if _column_exists(conn, "contacts", "phone_number"):
        op.drop_column("contacts", "phone_number")
