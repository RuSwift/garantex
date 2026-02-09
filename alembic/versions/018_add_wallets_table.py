"""Add wallets table

Revision ID: 018_wallets
Revises: 017_escrow_enabled
Create Date: 2026-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '018_wallets'
down_revision: Union[str, None] = '017_escrow_enabled'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create wallets table
    op.create_table(
        'wallets',
        sa.Column('id', sa.Integer(), nullable=False, comment='Primary key'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Wallet name (editable)'),
        sa.Column('encrypted_mnemonic', sa.Text(), nullable=False, comment='Encrypted mnemonic phrase'),
        sa.Column('tron_address', sa.String(length=34), nullable=False, comment='TRON address'),
        sa.Column('ethereum_address', sa.String(length=42), nullable=False, comment='Ethereum address'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_wallets_id', 'wallets', ['id'], unique=False)
    op.create_index('ix_wallets_tron_address', 'wallets', ['tron_address'], unique=True)
    op.create_index('ix_wallets_ethereum_address', 'wallets', ['ethereum_address'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_wallets_ethereum_address', table_name='wallets')
    op.drop_index('ix_wallets_tron_address', table_name='wallets')
    op.drop_index('ix_wallets_id', table_name='wallets')
    
    # Drop table
    op.drop_table('wallets')

