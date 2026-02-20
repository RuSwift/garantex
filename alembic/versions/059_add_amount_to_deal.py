"""Add amount column to deal table

Revision ID: 059_add_amount_to_deal
Revises: 058_add_payout_txn_to_deal
Create Date: 2026-02-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '059_add_amount_to_deal'
down_revision: Union[str, None] = '058_add_payout_txn_to_deal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deal',
        sa.Column(
            'amount',
            sa.Numeric(20, 8),
            nullable=True,
            comment='Сумма сделки'
        )
    )


def downgrade() -> None:
    op.drop_column('deal', 'amount')
