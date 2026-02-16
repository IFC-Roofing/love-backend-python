"""create postcards table

Revision ID: b2c3d4e5f6789
Revises: a9b7500e5228
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6789"
down_revision: Union[str, None] = "a9b7500e5228"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table: str) -> bool:
    r = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :t"
        ),
        {"t": table},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "postcards"):
        return
    op.create_table(
        "postcards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("front_image_path", sa.String(), nullable=False),
        sa.Column("back_image_path", sa.String(), nullable=False),
        sa.Column("personal_message", sa.Text(), nullable=True),
        sa.Column("qr_code_data", sa.String(), nullable=True),
        sa.Column("design_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("image_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_postcards_user_id"), "postcards", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_postcards_user_id"), table_name="postcards")
    op.drop_table("postcards")
