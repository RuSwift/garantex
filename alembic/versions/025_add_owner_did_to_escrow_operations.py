"""Add owner_did field to escrow_operations table

Revision ID: 025_owner_did_escrow
Revises: 024_conversation_id
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '025_owner_did_escrow'
down_revision: Union[str, None] = '0b1d2be408bb'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add owner_did column to escrow_operations table as NOT NULL
    # Note: If there are existing records in the table, they need to be populated with owner_did
    # before applying this migration, or the migration will fail
    op.add_column('escrow_operations', sa.Column('owner_did', sa.String(length=255), nullable=False, comment='Owner DID - пользователь, которому принадлежит escrow'))
    
    # Create index on owner_did for efficient queries
    op.create_index('ix_escrow_operations_owner_did', 'escrow_operations', ['owner_did'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_escrow_operations_owner_did', table_name='escrow_operations')
    
    # Drop column
    op.drop_column('escrow_operations', 'owner_did')

