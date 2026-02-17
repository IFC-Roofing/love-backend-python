"""postcard video QR fields (video_s3_url, video_thumbnail_path, video_qr_image_path)

Revision ID: g78901234567
Revises: f67890123456
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "g78901234567"
down_revision: Union[str, None] = "a78901234567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"),
        {"t": table, "c": column},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    for col_name, col_type in [
        ("video_s3_url", sa.String()),
        ("video_thumbnail_path", sa.String()),
        ("video_qr_image_path", sa.String()),
    ]:
        if not _column_exists(conn, "postcards", col_name):
            op.add_column("postcards", sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    for col in ("video_s3_url", "video_thumbnail_path", "video_qr_image_path"):
        try:
            op.drop_column("postcards", col)
        except Exception:
            pass
