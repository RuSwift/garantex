"""Add status to escrow_operations table

Revision ID: 010_escrow_status
Revises: 009_arbiter_address
Create Date: 2026-02-07 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010_escrow_status'
down_revision: Union[str, None] = '009_arbiter_address'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column with default 'pending'
    op.add_column(
        'escrow_operations',
        sa.Column(
            'status',
            sa.String(length=50),
            nullable=False,
            server_default='pending',
            comment='Escrow status (pending, active, inactive)'
        )
    )
    # Add index on status for efficient queries
    op.create_index('ix_escrow_operations_status', 'escrow_operations', ['status'], unique=False)


def downgrade() -> None:
    # Remove index and column
    op.drop_index('ix_escrow_operations_status', table_name='escrow_operations')
    op.drop_column('escrow_operations', 'status')

