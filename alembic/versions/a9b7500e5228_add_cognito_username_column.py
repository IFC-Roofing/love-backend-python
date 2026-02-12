"""add cognito_username column

Revision ID: a9b7500e5228
Revises: 
Create Date: 2026-02-10 19:51:28.651957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b7500e5228'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column as nullable first (for existing rows)
    op.add_column('users', sa.Column('cognito_username', sa.String(), nullable=True))
    
    # Delete existing users (they don't have cognito_username and can't be backfilled)
    op.execute('DELETE FROM users')
    
    # Now make it NOT NULL
    op.alter_column('users', 'cognito_username', nullable=False)
    op.create_unique_constraint('uq_users_cognito_username', 'users', ['cognito_username'])


def downgrade() -> None:
    op.drop_constraint('uq_users_cognito_username', 'users', type_='unique')
    op.drop_column('users', 'cognito_username')
