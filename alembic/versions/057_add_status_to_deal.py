"""Add status column to deal table

Revision ID: 057_add_status_to_deal
Revises: 05611702a33f
Create Date: 2026-02-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '057_add_status_to_deal'
down_revision: Union[str, None] = '05611702a33f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deal',
        sa.Column(
            'status',
            sa.String(length=50),
            nullable=False,
            server_default='processing',
            comment='Статус сделки: processing, success, appeal, resolved_sender, resolved_receiver'
        )
    )
    op.create_index('ix_deal_status', 'deal', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_deal_status', table_name='deal')
    op.drop_column('deal', 'status')
