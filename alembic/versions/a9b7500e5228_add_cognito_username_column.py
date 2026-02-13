"""add cognito_username column

Revision ID: a9b7500e5228
Revises:
Create Date: 2026-02-10 19:51:28.651957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "a9b7500e5228"
down_revision: Union[str, None] = None
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


def _constraint_exists(conn, name: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": name}
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "users", "cognito_username"):
        op.add_column("users", sa.Column("cognito_username", sa.String(), nullable=True))
        op.execute("DELETE FROM users")
        op.alter_column("users", "cognito_username", nullable=False)
        op.create_unique_constraint(
            "uq_users_cognito_username", "users", ["cognito_username"]
        )
    elif not _constraint_exists(conn, "uq_users_cognito_username"):
        op.create_unique_constraint(
            "uq_users_cognito_username", "users", ["cognito_username"]
        )


def downgrade() -> None:
    op.drop_constraint("uq_users_cognito_username", "users", type_="unique")
    op.drop_column("users", "cognito_username")
