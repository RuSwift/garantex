"""Add escrow_txn table for escrow transactions and events

Revision ID: 032_escrow_txn_table
Revises: 031_encrypted_mnemonic_escrow
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '032_escrow_txn_table'
down_revision: Union[str, None] = '031_encrypted_mnemonic_escrow'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[Sequence[str], str, None] = None


def upgrade() -> None:
    # Create escrow_txn table
    op.create_table(
        'escrow_txn',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='Autoincrement primary key'),
        sa.Column('escrow_id', sa.BigInteger(), nullable=False, comment='Reference to escrow operation (one-to-one)'),
        sa.Column('txn', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Transaction or event data (JSONB)'),
        sa.Column('type', sa.String(length=20), nullable=False, comment="Type: 'txn' for transaction, 'event' for event"),
        sa.Column('comment', sa.Text(), nullable=False, comment='Comment describing the transaction or event'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['escrow_id'], ['escrow_operations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('escrow_id', name='uq_escrow_txn_escrow_id')
    )
    
    # Create indexes
    op.create_index('ix_escrow_txn_id', 'escrow_txn', ['id'], unique=False)
    op.create_index('ix_escrow_txn_escrow_id', 'escrow_txn', ['escrow_id'], unique=True)
    op.create_index('ix_escrow_txn_type', 'escrow_txn', ['type'], unique=False)
    op.create_index('ix_escrow_txn_data', 'escrow_txn', ['txn'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_escrow_txn_data', table_name='escrow_txn', postgresql_using='gin')
    op.drop_index('ix_escrow_txn_type', table_name='escrow_txn')
    op.drop_index('ix_escrow_txn_escrow_id', table_name='escrow_txn')
    op.drop_index('ix_escrow_txn_id', table_name='escrow_txn')
    
    # Drop table
    op.drop_table('escrow_txn')

