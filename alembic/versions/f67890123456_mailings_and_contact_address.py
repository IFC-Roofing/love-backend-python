"""mailings table and contact address columns

Revision ID: f67890123456
Revises: e5f678901234
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = "f67890123456"
down_revision: Union[str, None] = "e5f678901234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table: str) -> bool:
    r = conn.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"), {"t": table})
    return r.scalar() is not None


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"),
        {"t": table, "c": column},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "mailings"):
        op.create_table(
            "mailings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("postcard_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("recipient_name", sa.String(), nullable=True),
            sa.Column("recipient_address", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("external_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["postcard_id"], ["postcards.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        )
        op.create_index(op.f("ix_mailings_postcard_id"), "mailings", ["postcard_id"], unique=False)
        op.create_index(op.f("ix_mailings_user_id"), "mailings", ["user_id"], unique=False)
        op.create_index(op.f("ix_mailings_contact_id"), "mailings", ["contact_id"], unique=False)
        op.create_index(op.f("ix_mailings_external_id"), "mailings", ["external_id"], unique=False)

    for col in ("name", "address_line1", "city", "state", "postal_code", "country"):
        if not _column_exists(conn, "contacts", col):
            op.add_column("contacts", sa.Column(col, sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_index(op.f("ix_mailings_external_id"), table_name="mailings")
    op.drop_index(op.f("ix_mailings_contact_id"), table_name="mailings")
    op.drop_index(op.f("ix_mailings_user_id"), table_name="mailings")
    op.drop_index(op.f("ix_mailings_postcard_id"), table_name="mailings")
    op.drop_table("mailings")
    for col in ("name", "address_line1", "city", "state", "postal_code", "country"):
        op.drop_column("contacts", col)
