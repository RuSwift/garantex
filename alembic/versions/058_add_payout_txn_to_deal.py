"""Add payout_txn column to deal table

Revision ID: 058_add_payout_txn_to_deal
Revises: 057_add_status_to_deal
Create Date: 2026-02-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '058_add_payout_txn_to_deal'
down_revision: Union[str, None] = '057_add_status_to_deal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deal',
        sa.Column(
            'payout_txn',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Оффлайн-транзакция выплаты по сделке (зависит от status); null при appeal или без эскроу'
        )
    )


def downgrade() -> None:
    op.drop_column('deal', 'payout_txn')
