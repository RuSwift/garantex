"""Add account_permissions to wallets table

Revision ID: 019_account_permissions
Revises: 018_wallets
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '019_account_permissions'
down_revision: Union[str, None] = '018_wallets'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add account_permissions column to wallets table
    op.add_column('wallets', sa.Column('account_permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='TRON account permissions from blockchain'))


def downgrade() -> None:
    # Drop account_permissions column
    op.drop_column('wallets', 'account_permissions')

