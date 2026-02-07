"""Add balance_usdt field to wallet_users table

Revision ID: 015_balance_usdt_wallet_users
Revises: 014_is_verified_wallet_users
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Numeric


# revision identifiers, used by Alembic.
revision = '015_balance_usdt_wallet_users'
down_revision = '014_is_verified_wallet_users'
branch_labels = None
depends_on = None


def upgrade():
    # Add balance_usdt column to wallet_users table
    op.add_column('wallet_users', 
        sa.Column('balance_usdt', sa.Numeric(20, 8), nullable=False, server_default='0', comment='USDT balance')
    )


def downgrade():
    # Remove balance_usdt column from wallet_users table
    op.drop_column('wallet_users', 'balance_usdt')

