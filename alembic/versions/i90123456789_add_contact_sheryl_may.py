"""add contact Sheryl May

Revision ID: i90123456789
Revises: h89012345678
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "i90123456789"
down_revision: Union[str, None] = "h89012345678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same seed user as in a78901234567 (mair@ifcroofing.com)
SEED_USER_ID = "df8e2c7d-0225-4ac0-b9c9-65cf422860f3"

CONTACT = {
    "name": "Sheryl May",
    "email": "sheryl@ifcroofing.com",
    "phone_number": None,
    "address_line1": "5115 Colleyville Boulevard",
    "city": "Colleyville",
    "state": "TX",
    "postal_code": "76034",
    "country": "US",
}


def _user_exists(conn, user_id: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM users WHERE id = :uid LIMIT 1"),
        {"uid": user_id},
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
    # Only insert if seed user exists (e.g. dev); skip in production if user not present
    if not _user_exists(conn, SEED_USER_ID):
        return
    if _contact_exists(conn, SEED_USER_ID, CONTACT["email"]):
        return
    conn.execute(
        text("""
            INSERT INTO contacts (id, user_id, email, phone_number, name, address_line1, city, state, postal_code, country)
            VALUES (gen_random_uuid(), :uid, :email, :phone_number, :name, :address_line1, :city, :state, :postal_code, :country)
        """),
        {
            "uid": SEED_USER_ID,
            "email": CONTACT["email"],
            "phone_number": CONTACT["phone_number"],
            "name": CONTACT["name"],
            "address_line1": CONTACT["address_line1"],
            "city": CONTACT["city"],
            "state": CONTACT["state"],
            "postal_code": CONTACT["postal_code"],
            "country": CONTACT["country"],
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM contacts WHERE user_id = :uid AND email = :email"),
        {"uid": SEED_USER_ID, "email": CONTACT["email"]},
    )
