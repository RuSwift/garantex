"""Add commissioners to deal and payout_executor_address to escrow

Revision ID: 063_commissioners_payout_executor
Revises: 062_add_payout_txn_hash_to_deal
Create Date: 2026-02-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '063_commissioners_payout_executor'
down_revision: Union[str, None] = '062_add_payout_txn_hash_to_deal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deal',
        sa.Column(
            'commissioners',
            JSONB,
            nullable=True,
            comment='Комиссионеры: массив {address, amount} для атомарной выплаты'
        )
    )
    op.add_column(
        'escrow_operations',
        sa.Column(
            'payout_executor_address',
            sa.String(255),
            nullable=True,
            comment='Адрес контракта PayoutAndFeesExecutor (TRON)'
        )
    )


def downgrade() -> None:
    op.drop_column('deal', 'commissioners')
    op.drop_column('escrow_operations', 'payout_executor_address')
