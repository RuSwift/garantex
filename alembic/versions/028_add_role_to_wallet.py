"""Add role to wallets table

Revision ID: 028_add_role_to_wallet
Revises: 027_replace_participants_fields
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '028_add_role_to_wallet'
down_revision: Union[str, None] = '027_replace_participants_fields'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add role column to wallets table
    op.add_column('wallets', sa.Column('role', sa.String(length=255), nullable=True, comment='Wallet role'))


def downgrade() -> None:
    # Drop role column
    op.drop_column('wallets', 'role')

