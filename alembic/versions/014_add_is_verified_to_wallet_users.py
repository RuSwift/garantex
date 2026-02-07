"""Add is_verified field to wallet_users table

Revision ID: 014_is_verified_wallet_users
Revises: 013_advertisements_table
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014_is_verified_wallet_users'
down_revision = '013_advertisements_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_verified column to wallet_users table
    op.add_column('wallet_users', 
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false(), comment='Whether the user is verified (document verification)')
    )


def downgrade():
    # Remove is_verified column from wallet_users table
    op.drop_column('wallet_users', 'is_verified')

