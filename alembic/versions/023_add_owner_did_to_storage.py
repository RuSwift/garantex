"""Add owner_did field to storage table

Revision ID: 023_owner_did_storage
Revises: 022_deal_uid_storage
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '023_owner_did_storage'
down_revision: Union[str, None] = '022_deal_uid_storage'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add owner_did column to storage table
    op.add_column('storage', sa.Column('owner_did', sa.String(length=255), nullable=True, comment='Owner DID - пользователь, которому принадлежит ledger'))
    
    # Create index on owner_did for efficient queries
    op.create_index('ix_storage_owner_did', 'storage', ['owner_did'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_storage_owner_did', table_name='storage')
    
    # Drop column
    op.drop_column('storage', 'owner_did')

