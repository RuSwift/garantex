"""Initial migration: create node_settings table

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create node_settings table
    op.create_table(
        'node_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('encrypted_mnemonic', sa.Text(), nullable=True, comment='Encrypted mnemonic phrase'),
        sa.Column('encrypted_pem', sa.Text(), nullable=True, comment='Encrypted PEM key data'),
        sa.Column('key_type', sa.String(length=20), nullable=False, server_default='mnemonic', comment='Type of key: mnemonic or pem'),
        sa.Column('ethereum_address', sa.String(length=42), nullable=True, comment='Ethereum address'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether this key is currently active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on ethereum_address
    op.create_index('ix_node_settings_ethereum_address', 'node_settings', ['ethereum_address'], unique=True)
    op.create_index('ix_node_settings_id', 'node_settings', ['id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_node_settings_id', table_name='node_settings')
    op.drop_index('ix_node_settings_ethereum_address', table_name='node_settings')
    
    # Drop table
    op.drop_table('node_settings')

