"""Add deals table

Revision ID: 020_deals
Revises: 019_account_permissions
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '020_deals'
down_revision: Union[str, None] = '019_account_permissions'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create deals table
    op.create_table(
        'deals',
        sa.Column('order_id', sa.BigInteger(), autoincrement=True, nullable=False, comment='Autoincrement primary key'),
        sa.Column('sender_did', sa.String(length=255), nullable=False, comment='Sender DID'),
        sa.Column('receiver_did', sa.String(length=255), nullable=False, comment='Receiver DID'),
        sa.Column('arbiter_did', sa.String(length=255), nullable=False, comment='Arbiter DID'),
        sa.Column('escrow_id', sa.BigInteger(), nullable=True, comment='Reference to escrow operation'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='Deal title'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.PrimaryKeyConstraint('order_id'),
        sa.ForeignKeyConstraint(['escrow_id'], ['escrow_operations.id'], ondelete='SET NULL')
    )
    
    # Create indexes
    op.create_index('ix_deals_order_id', 'deals', ['order_id'], unique=False)
    op.create_index('ix_deals_sender_did', 'deals', ['sender_did'], unique=False)
    op.create_index('ix_deals_receiver_did', 'deals', ['receiver_did'], unique=False)
    op.create_index('ix_deals_arbiter_did', 'deals', ['arbiter_did'], unique=False)
    op.create_index('ix_deals_escrow_id', 'deals', ['escrow_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_deals_escrow_id', table_name='deals')
    op.drop_index('ix_deals_arbiter_did', table_name='deals')
    op.drop_index('ix_deals_receiver_did', table_name='deals')
    op.drop_index('ix_deals_sender_did', table_name='deals')
    op.drop_index('ix_deals_order_id', table_name='deals')
    
    # Drop table
    op.drop_table('deals')

