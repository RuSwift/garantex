"""Add deposit_txn_hash column to deal table

Revision ID: 060_add_deposit_txn_hash_to_deal
Revises: 059_add_amount_to_deal
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '060_add_deposit_txn_hash_to_deal'
down_revision: Union[str, None] = '059_add_amount_to_deal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deal',
        sa.Column(
            'deposit_txn_hash',
            sa.String(66),
            nullable=True,
            comment='Hash транзакции депозита в эскроу'
        )
    )
    op.create_index('ix_deal_deposit_txn_hash', 'deal', ['deposit_txn_hash'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_deal_deposit_txn_hash', table_name='deal')
    op.drop_column('deal', 'deposit_txn_hash')
