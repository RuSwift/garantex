"""Change deal status default to wait_deposit

Revision ID: 061_deal_default_wait_deposit
Revises: 060_add_deposit_txn_hash_to_deal
Create Date: 2026-02-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '061_deal_default_wait_deposit'
down_revision: Union[str, None] = '060_add_deposit_txn_hash_to_deal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'deal',
        'status',
        existing_type=sa.String(50),
        server_default=sa.text("'wait_deposit'"),
        comment='Статус сделки: wait_deposit, processing, success, appeal, resolved_sender, resolved_receiver'
    )


def downgrade() -> None:
    op.alter_column(
        'deal',
        'status',
        existing_type=sa.String(50),
        server_default=sa.text("'processing'"),
        comment='Статус сделки: processing, success, appeal, resolved_sender, resolved_receiver'
    )
