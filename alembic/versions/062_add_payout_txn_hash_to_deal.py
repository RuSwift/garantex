"""Add payout_txn_hash column to deal table

Revision ID: 062_add_payout_txn_hash_to_deal
Revises: 061_deal_default_wait_deposit
Create Date: 2026-02-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '062_add_payout_txn_hash_to_deal'
down_revision: Union[str, None] = '061_deal_default_wait_deposit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deal',
        sa.Column(
            'payout_txn_hash',
            sa.String(66),
            nullable=True,
            comment='Hash подтверждённой транзакции выплаты'
        )
    )
    op.create_index('ix_deal_payout_txn_hash', 'deal', ['payout_txn_hash'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_deal_payout_txn_hash', table_name='deal')
    op.drop_column('deal', 'payout_txn_hash')
