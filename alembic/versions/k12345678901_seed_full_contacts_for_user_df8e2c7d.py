"""Seed contacts with full address for user df8e2c7d (mailing-ready)

Ensures user df8e2c7d-0225-4ac0-b9c9-65cf422860f3 has contacts that have all
required fields (email, name, address_line1, city, state, postal_code, country).
Phone is optional. Idempotent: inserts if missing, updates if existing so address is complete.

Revision ID: k12345678901
Revises: j01234567890
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "k12345678901"
down_revision: Union[str, None] = "j01234567890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TARGET_USER_ID = "df8e2c7d-0225-4ac0-b9c9-65cf422860f3"

# Contacts with full address (postal_code required for DMM). Phone optional.
FULL_CONTACTS = [
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


def _contact_exists(conn, user_id: str, email: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM contacts WHERE user_id = :uid AND email = :email LIMIT 1"),
        {"uid": user_id, "email": email},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    for c in FULL_CONTACTS:
        if _contact_exists(conn, TARGET_USER_ID, c["email"]):
            conn.execute(
                text("""
                    UPDATE contacts
                    SET name = :name, phone_number = :phone_number,
                        address_line1 = :address_line1, city = :city,
                        state = :state, postal_code = :postal_code, country = :country
                    WHERE user_id = :uid AND email = :email
                """),
                {
                    "uid": TARGET_USER_ID,
                    "email": c["email"],
                    "name": c["name"],
                    "phone_number": c["phone_number"],
                    "address_line1": c["address_line1"],
                    "city": c["city"],
                    "state": c["state"],
                    "postal_code": c["postal_code"],
                    "country": c["country"],
                },
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO contacts (id, user_id, email, phone_number, name, address_line1, city, state, postal_code, country)
                    VALUES (gen_random_uuid(), :uid, :email, :phone_number, :name, :address_line1, :city, :state, :postal_code, :country)
                """),
                {
                    "uid": TARGET_USER_ID,
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
    # Do not remove contacts; only ensure full data was set. Downgrade is a no-op.
    # To revert data you would need to know previous values per row.
    pass
