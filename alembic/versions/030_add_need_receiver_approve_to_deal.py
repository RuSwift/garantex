"""Add need_receiver_approve field to deal table

Revision ID: 030_need_receiver_approve_deal
Revises: 029_change_wallet_address_unique
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '030_need_receiver_approve_deal'
down_revision: Union[str, None] = '029_change_wallet_address_unique'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add need_receiver_approve column to deal table
    op.add_column(
        'deal',
        sa.Column(
            'need_receiver_approve',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment='Требуется ли одобрение получателя'
        )
    )


def downgrade() -> None:
    # Drop need_receiver_approve column
    op.drop_column('deal', 'need_receiver_approve')

