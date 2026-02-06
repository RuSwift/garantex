"""Add admin_users table

Revision ID: 002_admin_users
Revises: 5a3e7b1c8f2d
Create Date: 2026-02-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_admin_users'
down_revision: Union[str, None] = '5a3e7b1c8f2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('auth_method', sa.String(length=20), nullable=False, comment='Auth method: password or tron'),
        sa.Column('username', sa.String(length=255), nullable=True, comment='Admin username'),
        sa.Column('password_hash', sa.Text(), nullable=True, comment='Hashed password (bcrypt)'),
        sa.Column('tron_address', sa.String(length=34), nullable=True, comment='Whitelisted TRON address'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether this admin is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_admin_users_id', 'admin_users', ['id'], unique=False)
    op.create_index('ix_admin_users_username', 'admin_users', ['username'], unique=True)
    op.create_index('ix_admin_users_tron_address', 'admin_users', ['tron_address'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_admin_users_tron_address', table_name='admin_users')
    op.drop_index('ix_admin_users_username', table_name='admin_users')
    op.drop_index('ix_admin_users_id', table_name='admin_users')
    
    # Drop table
    op.drop_table('admin_users')

