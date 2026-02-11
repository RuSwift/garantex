"""Add deal table with base58 UUID identifier

Revision ID: 021_deal
Revises: 020_deals
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '021_deal'
down_revision: Union[str, None] = '020_deals'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create deal table
    op.create_table(
        'deal',
        sa.Column('pk', sa.BigInteger(), autoincrement=True, nullable=False, comment='Autoincrement primary key'),
        sa.Column('uid', sa.String(length=255), nullable=False, comment='Base58 UUID identifier (primary identifier)'),
        sa.Column('participants', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Array of participant DID identifiers'),
        sa.Column('label', sa.Text(), nullable=False, comment='Text description of the deal'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.PrimaryKeyConstraint('pk')
    )
    
    # Create indexes
    op.create_index('ix_deal_pk', 'deal', ['pk'], unique=False)
    op.create_index('ix_deal_uid', 'deal', ['uid'], unique=True)
    # Create GIN index on participants for efficient JSONB queries
    op.create_index('ix_deal_participants', 'deal', ['participants'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_deal_participants', table_name='deal', postgresql_using='gin')
    op.drop_index('ix_deal_uid', table_name='deal')
    op.drop_index('ix_deal_pk', table_name='deal')
    
    # Drop table
    op.drop_table('deal')

