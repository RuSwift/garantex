"""Add connections table for DIDComm protocol states

Revision ID: 5a3e7b1c8f2d
Revises: 0c28b5f84a70
Create Date: 2026-02-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5a3e7b1c8f2d'
down_revision: Union[str, None] = '0c28b5f84a70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create connections table
    op.create_table(
        'connections',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='Autoincrement primary key'),
        sa.Column('connection_id', sa.String(length=255), nullable=False, comment='Unique connection identifier (message ID)'),
        sa.Column('my_did', sa.String(length=255), nullable=False, comment='Our DID'),
        sa.Column('their_did', sa.String(length=255), nullable=True, comment='Their DID (null for pending invitations)'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending', comment='Connection status'),
        sa.Column('connection_type', sa.String(length=20), nullable=False, comment='Type of connection message'),
        sa.Column('label', sa.String(length=255), nullable=True, comment='Human-readable label'),
        sa.Column('connection_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional connection metadata'),
        sa.Column('message_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Original DIDComm message data'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.Column('established_at', sa.DateTime(timezone=True), nullable=True, comment='When connection was established (UTC)'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_connections_id', 'connections', ['id'], unique=False)
    op.create_index('ix_connections_connection_id', 'connections', ['connection_id'], unique=True)
    op.create_index('ix_connections_my_did', 'connections', ['my_did'], unique=False)
    op.create_index('ix_connections_their_did', 'connections', ['their_did'], unique=False)
    op.create_index('ix_connections_status', 'connections', ['status'], unique=False)
    
    # Create composite indexes for efficient queries
    op.create_index('ix_connections_my_did_status', 'connections', ['my_did', 'status'], unique=False)
    op.create_index('ix_connections_their_did_status', 'connections', ['their_did', 'status'], unique=False)
    
    # Create GIN index on JSONB columns for efficient JSON queries
    op.create_index('ix_connections_connection_metadata', 'connections', ['connection_metadata'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_connections_connection_metadata', table_name='connections', postgresql_using='gin')
    op.drop_index('ix_connections_their_did_status', table_name='connections')
    op.drop_index('ix_connections_my_did_status', table_name='connections')
    op.drop_index('ix_connections_status', table_name='connections')
    op.drop_index('ix_connections_their_did', table_name='connections')
    op.drop_index('ix_connections_my_did', table_name='connections')
    op.drop_index('ix_connections_connection_id', table_name='connections')
    op.drop_index('ix_connections_id', table_name='connections')
    
    # Drop table
    op.drop_table('connections')

