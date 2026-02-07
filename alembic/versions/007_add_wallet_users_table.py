"""Add wallet_users table

Revision ID: 007_wallet_users
Revises: 006_add_service_endpoint
Create Date: 2026-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_wallet_users'
down_revision: Union[str, None] = '006_add_service_endpoint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create wallet_users table
    op.create_table(
        'wallet_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wallet_address', sa.String(length=255), nullable=False, comment='Wallet address (TRON: 34 chars, ETH: 42 chars)'),
        sa.Column('blockchain', sa.String(length=20), nullable=False, comment='Blockchain type: tron, ethereum, bitcoin, etc.'),
        sa.Column('nickname', sa.String(length=100), nullable=False, comment='User display name'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_wallet_users_id', 'wallet_users', ['id'], unique=False)
    op.create_index('ix_wallet_users_wallet_address', 'wallet_users', ['wallet_address'], unique=True)
    op.create_index('ix_wallet_users_blockchain', 'wallet_users', ['blockchain'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_wallet_users_blockchain', table_name='wallet_users')
    op.drop_index('ix_wallet_users_wallet_address', table_name='wallet_users')
    op.drop_index('ix_wallet_users_id', table_name='wallet_users')
    
    # Drop table
    op.drop_table('wallet_users')

