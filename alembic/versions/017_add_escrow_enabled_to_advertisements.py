"""Add escrow_enabled field to advertisements table

Revision ID: 017_escrow_enabled
Revises: 016_billing_table
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017_escrow_enabled'
down_revision = '016_billing_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add escrow_enabled column to advertisements table
    op.add_column(
        'advertisements',
        sa.Column(
            'escrow_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment='Whether escrow deals are enabled (agent conducts deal using their liquidity, debiting funds from escrow address upon service delivery)'
        )
    )


def downgrade():
    # Remove escrow_enabled column
    op.drop_column('advertisements', 'escrow_enabled')

