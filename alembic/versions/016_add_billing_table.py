"""Add billing table

Revision ID: 016_billing_table
Revises: 015_balance_usdt_wallet_users
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Numeric


# revision identifiers, used by Alembic.
revision = '016_billing_table'
down_revision = '015_balance_usdt_wallet_users'
branch_labels = None
depends_on = None


def upgrade():
    # Create billing table
    op.create_table(
        'billing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wallet_user_id', sa.Integer(), nullable=False, comment='Reference to wallet user'),
        sa.Column('usdt_amount', sa.Numeric(20, 8), nullable=False, comment='USDT amount: positive for deposit, negative for withdrawal'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Transaction timestamp'),
        sa.ForeignKeyConstraint(['wallet_user_id'], ['wallet_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_id'), 'billing', ['id'], unique=False)
    op.create_index(op.f('ix_billing_wallet_user_id'), 'billing', ['wallet_user_id'], unique=False)
    op.create_index(op.f('ix_billing_created_at'), 'billing', ['created_at'], unique=False)


def downgrade():
    # Drop billing table
    op.drop_index(op.f('ix_billing_created_at'), table_name='billing')
    op.drop_index(op.f('ix_billing_wallet_user_id'), table_name='billing')
    op.drop_index(op.f('ix_billing_id'), table_name='billing')
    op.drop_table('billing')

