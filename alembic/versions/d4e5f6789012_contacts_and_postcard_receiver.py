"""contacts table and postcards.receiver_contact_id

Revision ID: d4e5f6789012
Revises: b2c3d4e5f6789
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6789012"
down_revision: Union[str, None] = "b2c3d4e5f6789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_USER_ID = "df8e2c7d-0225-4ac0-b9c9-65cf422860f3"


def _table_exists(conn, table: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table},
    )
    return r.scalar() is not None


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

    # Create contacts table
    if not _table_exists(conn, "contacts"):
        op.create_table(
            "contacts",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index(op.f("ix_contacts_user_id"), "contacts", ["user_id"], unique=False)
        op.create_index(op.f("ix_contacts_email"), "contacts", ["email"], unique=False)

    # Add receiver_contact_id to postcards
    if not _column_exists(conn, "postcards", "receiver_contact_id"):
        op.add_column(
            "postcards",
            sa.Column(
                "receiver_contact_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "fk_postcards_receiver_contact_id_contacts",
            "postcards",
            "contacts",
            ["receiver_contact_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            op.f("ix_postcards_receiver_contact_id"),
            "postcards",
            ["receiver_contact_id"],
            unique=False,
        )

    # Seed contacts for user df8e2c7d-0225-4ac0-b9c9-65cf422860f3 (only if user exists and no contacts yet)
    if _table_exists(conn, "contacts"):
        user_exists = conn.execute(
            text("SELECT 1 FROM users WHERE id = :uid LIMIT 1"),
            {"uid": SEED_USER_ID},
        ).scalar() is not None
        already_seeded = conn.execute(
            text("SELECT 1 FROM contacts WHERE user_id = :uid LIMIT 1"),
            {"uid": SEED_USER_ID},
        ).scalar() is not None
        if user_exists and not already_seeded:
            conn.execute(
                text("""
                    INSERT INTO contacts (id, user_id, email)
                    VALUES
                        (gen_random_uuid(), :uid, 'alice@example.com'),
                        (gen_random_uuid(), :uid, 'bob.smith@test.org'),
                        (gen_random_uuid(), :uid, 'carol.jones@gmail.com'),
                        (gen_random_uuid(), :uid, 'dave.wilson@company.co'),
                        (gen_random_uuid(), :uid, 'eve.brown@mail.io')
                """),
                {"uid": SEED_USER_ID},
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_postcards_receiver_contact_id"), table_name="postcards")
    op.drop_constraint(
        "fk_postcards_receiver_contact_id_contacts",
        "postcards",
        type_="foreignkey",
    )
    op.drop_column("postcards", "receiver_contact_id")

    op.drop_index(op.f("ix_contacts_email"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_user_id"), table_name="contacts")
    op.drop_table("contacts")
