"""Add arbiter_address to escrow_operations table

Revision ID: 009_arbiter_address
Revises: 008_escrow_model
Create Date: 2026-02-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009_arbiter_address'
down_revision: Union[str, None] = '008_escrow_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add arbiter_address column to escrow_operations table
    op.add_column(
        'escrow_operations',
        sa.Column('arbiter_address', sa.String(length=255), nullable=True, comment='Arbiter address (can be changed by participants)')
    )


def downgrade() -> None:
    # Remove arbiter_address column
    op.drop_column('escrow_operations', 'arbiter_address')

