"""Add advertisements table for user marketplace offers

Revision ID: 013_advertisements_table
Revises: 65c2e0ae79f7
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '013_advertisements_table'
down_revision = '65c2e0ae79f7'
branch_labels = None
depends_on = None


def upgrade():
    # Create advertisements table
    op.create_table(
        'advertisements',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='Autoincrement primary key'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='User ID from wallet_users table'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Display name for the advertisement'),
        sa.Column('description', sa.Text(), nullable=False, comment='Detailed description of the offer'),
        sa.Column('fee', sa.String(length=10), nullable=False, comment="Fee percentage (e.g. '2.5')"),
        sa.Column('min_limit', sa.Integer(), nullable=False, comment='Minimum transaction limit in USDT'),
        sa.Column('max_limit', sa.Integer(), nullable=False, comment='Maximum transaction limit in USDT'),
        sa.Column('currency', sa.String(length=10), nullable=False, comment='Currency code (USD, EUR, RUB, etc.)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true(), comment='Whether the advertisement is active'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false(), comment='Whether the advertisement is verified by admin'),
        sa.Column('rating', sa.String(length=10), nullable=True, server_default='0.0', comment="User rating (e.g. '4.9')"),
        sa.Column('deals_count', sa.Integer(), nullable=False, server_default='0', comment='Number of completed deals'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.PrimaryKeyConstraint('id'),
        comment='User advertisements (offers) on marketplace'
    )
    
    # Create indexes
    op.create_index('ix_advertisements_id', 'advertisements', ['id'])
    op.create_index('ix_advertisements_user_id', 'advertisements', ['user_id'])
    op.create_index('ix_advertisements_user_active', 'advertisements', ['user_id', 'is_active'])
    op.create_index('ix_advertisements_currency_active', 'advertisements', ['currency', 'is_active'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_advertisements_currency_active', table_name='advertisements')
    op.drop_index('ix_advertisements_user_active', table_name='advertisements')
    op.drop_index('ix_advertisements_user_id', table_name='advertisements')
    op.drop_index('ix_advertisements_id', table_name='advertisements')
    
    # Drop table
    op.drop_table('advertisements')

