"""Add access_to_admin_panel to wallet_users table

Revision ID: 012_access_to_admin_panel
Revises: 011_participant_addresses
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012_access_to_admin_panel'
down_revision = '011_participant_addresses'
branch_labels = None
depends_on = None


def upgrade():
    # Add access_to_admin_panel column with default False
    op.add_column('wallet_users', sa.Column('access_to_admin_panel', sa.Boolean(), nullable=False, server_default=sa.false(), comment='Access to admin panel'))


def downgrade():
    # Drop access_to_admin_panel column
    op.drop_column('wallet_users', 'access_to_admin_panel')

