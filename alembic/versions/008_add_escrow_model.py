"""Add escrow_operations table for multisig escrow configurations

Revision ID: 008_escrow_model
Revises: 007_wallet_users
Create Date: 2026-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_escrow_model'
down_revision: Union[str, None] = '007_wallet_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create escrow_operations table
    op.create_table(
        'escrow_operations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='Autoincrement primary key'),
        sa.Column('blockchain', sa.String(length=50), nullable=False, comment='Blockchain name (tron, eth, etc.)'),
        sa.Column('network', sa.String(length=50), nullable=False, comment='Network name (mainnet, testnet, etc.)'),
        sa.Column('escrow_type', sa.String(length=20), nullable=False, comment='Escrow type (multisig, contract)'),
        sa.Column('escrow_address', sa.String(length=255), nullable=False, comment='Escrow address in blockchain'),
        sa.Column('multisig_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='MultisigConfig configuration (JSONB)'),
        sa.Column('address_roles', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Mapping of addresses to roles (participant, arbiter)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_escrow_operations_id', 'escrow_operations', ['id'], unique=False)
    op.create_index('ix_escrow_operations_blockchain', 'escrow_operations', ['blockchain'], unique=False)
    op.create_index('ix_escrow_operations_network', 'escrow_operations', ['network'], unique=False)
    
    # Create GIN index on multisig_config for efficient JSONB queries
    op.create_index('ix_escrow_multisig_config', 'escrow_operations', ['multisig_config'], unique=False, postgresql_using='gin')
    
    # Create unique constraint on (blockchain, network, escrow_address)
    op.create_index('uq_escrow_blockchain_network_address', 'escrow_operations', ['blockchain', 'network', 'escrow_address'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('uq_escrow_blockchain_network_address', table_name='escrow_operations')
    op.drop_index('ix_escrow_multisig_config', table_name='escrow_operations', postgresql_using='gin')
    op.drop_index('ix_escrow_operations_network', table_name='escrow_operations')
    op.drop_index('ix_escrow_operations_blockchain', table_name='escrow_operations')
    op.drop_index('ix_escrow_operations_id', table_name='escrow_operations')
    
    # Drop table
    op.drop_table('escrow_operations')

