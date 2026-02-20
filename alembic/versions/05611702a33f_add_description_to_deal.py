"""add_description_to_deal

Revision ID: 05611702a33f
Revises: 033_add_counter_to_escrow_txn
Create Date: 2026-02-20 18:15:06.203499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05611702a33f'
down_revision: Union[str, None] = '033_add_counter_to_escrow_txn'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add description column to deal table
    op.add_column(
        'deal',
        sa.Column(
            'description',
            sa.Text(),
            nullable=True,
            comment='Описание сделки (дополнительное описание, отдельно от label)'
        )
    )


def downgrade() -> None:
    # Drop description column
    op.drop_column('deal', 'description')

