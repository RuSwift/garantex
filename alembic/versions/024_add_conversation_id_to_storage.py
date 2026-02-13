"""Add conversation_id field to storage table

Revision ID: 024_conversation_id
Revises: 023_owner_did_storage
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '024_conversation_id'
down_revision: Union[str, None] = '023_owner_did_storage'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add conversation_id column to storage table
    op.add_column('storage', sa.Column('conversation_id', sa.String(length=255), nullable=True, comment='Conversation ID для группировки сообщений'))
    
    # Create index on conversation_id for efficient queries
    op.create_index('ix_storage_conversation_id', 'storage', ['conversation_id'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_storage_conversation_id', table_name='storage')
    
    # Drop column
    op.drop_column('storage', 'conversation_id')

