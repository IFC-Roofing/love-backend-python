"""add user profile_image_url (S3 URL)

Revision ID: e5f678901234
Revises: d4e5f6789012
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "e5f678901234"
down_revision: Union[str, None] = "d4e5f6789012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "users", "profile_image_url"):
        op.add_column("users", sa.Column("profile_image_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_image_url")
