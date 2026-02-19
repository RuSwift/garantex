"""Add counter column to escrow_txn table

Revision ID: 033_add_counter_to_escrow_txn
Revises: 032_escrow_txn_table
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '033_add_counter_to_escrow_txn'
down_revision: Union[str, None] = '032_escrow_txn_table'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add counter column with default value 1
    op.add_column(
        'escrow_txn',
        sa.Column(
            'counter',
            sa.Integer(),
            nullable=False,
            server_default='1',
            comment='Counter for duplicate events (incremented when same event occurs)'
        )
    )


def downgrade() -> None:
    # Remove counter column
    op.drop_column('escrow_txn', 'counter')

