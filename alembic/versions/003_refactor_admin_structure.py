"""refactor admin structure: one admin + multiple tron addresses

Revision ID: 003_refactor_admin
Revises: 002_admin_users
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '003_refactor_admin'
down_revision = '002_admin_users'
branch_labels = None
depends_on = None


def upgrade():
    """
    Refactor admin structure:
    - Create admin_tron_addresses table
    - Remove auth_method, tron_address, is_active from admin_users
    - Migrate existing data
    """
    
    # 1. Create new table for TRON addresses
    op.create_table(
        'admin_tron_addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tron_address', sa.String(length=34), nullable=False, comment='Whitelisted TRON address'),
        sa.Column('label', sa.String(length=255), nullable=True, comment='Optional label for this address'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Whether this address is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_tron_addresses_id'), 'admin_tron_addresses', ['id'], unique=False)
    op.create_index(op.f('ix_admin_tron_addresses_tron_address'), 'admin_tron_addresses', ['tron_address'], unique=True)
    
    # 2. Make auth_method nullable temporarily (to allow data migration)
    op.alter_column('admin_users', 'auth_method', nullable=True)
    
    # 3. Migrate existing data
    connection = op.get_bind()
    
    # Find password admin (if exists)
    password_admins = connection.execute(
        text("SELECT * FROM admin_users WHERE auth_method = 'password' ORDER BY created_at LIMIT 1")
    ).fetchall()
    
    # Find all TRON admins
    tron_admins = connection.execute(
        text("SELECT * FROM admin_users WHERE auth_method = 'tron' ORDER BY created_at")
    ).fetchall()
    
    # Clear admin_users table
    connection.execute(text("DELETE FROM admin_users"))
    
    # Create single admin user
    if password_admins:
        # If there was a password admin, create admin with password
        admin = password_admins[0]
        connection.execute(
            text(
                "INSERT INTO admin_users (id, username, password_hash, created_at, updated_at) "
                "VALUES (1, :username, :password_hash, :created_at, :updated_at)"
            ),
            {
                'username': admin.username,
                'password_hash': admin.password_hash,
                'created_at': admin.created_at,
                'updated_at': admin.updated_at
            }
        )
    else:
        # No password admin, create empty admin (TRON-only)
        connection.execute(
            text("INSERT INTO admin_users (id, username, password_hash) VALUES (1, NULL, NULL)")
        )
    
    # Migrate TRON addresses to new table
    for tron_admin in tron_admins:
        connection.execute(
            text(
                "INSERT INTO admin_tron_addresses (tron_address, is_active, created_at, updated_at) "
                "VALUES (:tron_address, :is_active, :created_at, :updated_at)"
            ),
            {
                'tron_address': tron_admin.tron_address,
                'is_active': tron_admin.is_active,
                'created_at': tron_admin.created_at,
                'updated_at': tron_admin.updated_at
            }
        )
    
    # 4. Drop old columns from admin_users
    op.drop_column('admin_users', 'is_active')
    op.drop_column('admin_users', 'tron_address')
    op.drop_column('admin_users', 'auth_method')


def downgrade():
    """
    Rollback the refactoring (if needed)
    """
    # Add back old columns
    op.add_column('admin_users', sa.Column('auth_method', sa.String(length=20), nullable=True))
    op.add_column('admin_users', sa.Column('tron_address', sa.String(length=34), nullable=True))
    op.add_column('admin_users', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True))
    
    # Migrate data back (simplified - just migrate TRON addresses as separate admins)
    connection = op.get_bind()
    
    tron_addresses = connection.execute(
        text("SELECT * FROM admin_tron_addresses ORDER BY created_at")
    ).fetchall()
    
    for addr in tron_addresses:
        connection.execute(
            text(
                "INSERT INTO admin_users (auth_method, tron_address, is_active, created_at, updated_at) "
                "VALUES ('tron', :tron_address, :is_active, :created_at, :updated_at)"
            ),
            {
                'tron_address': addr.tron_address,
                'is_active': addr.is_active,
                'created_at': addr.created_at,
                'updated_at': addr.updated_at
            }
        )
    
    # Update password admin to have auth_method
    connection.execute(
        text("UPDATE admin_users SET auth_method = 'password' WHERE username IS NOT NULL")
    )
    
    # Make auth_method NOT NULL
    op.alter_column('admin_users', 'auth_method', nullable=False)
    
    # Drop new table
    op.drop_index(op.f('ix_admin_tron_addresses_tron_address'), table_name='admin_tron_addresses')
    op.drop_index(op.f('ix_admin_tron_addresses_id'), table_name='admin_tron_addresses')
    op.drop_table('admin_tron_addresses')

