"""Add deal_uid field to storage table

Revision ID: 022_deal_uid_storage
Revises: 021_deal
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '022_deal_uid_storage'
down_revision: Union[str, None] = '021_deal'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add deal_uid column to storage table
    op.add_column('storage', sa.Column('deal_uid', sa.String(length=255), nullable=True, comment='Deal UID (base58 UUID) reference'))
    
    # Create index on deal_uid for efficient queries
    op.create_index('ix_storage_deal_uid', 'storage', ['deal_uid'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_storage_deal_uid', table_name='storage')
    
    # Drop column
    op.drop_column('storage', 'deal_uid')

