"""Add participant addresses to escrow_operations table

Revision ID: 011_participant_addresses
Revises: 010_escrow_status
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_participant_addresses'
down_revision = '010_escrow_status'
branch_labels = None
depends_on = None


def upgrade():
    # Add participant address columns
    op.add_column('escrow_operations', sa.Column('participant1_address', sa.String(length=255), nullable=True, comment='First participant address'))
    op.add_column('escrow_operations', sa.Column('participant2_address', sa.String(length=255), nullable=True, comment='Second participant address'))
    
    # Create indexes
    op.create_index('ix_escrow_operations_participant1_address', 'escrow_operations', ['participant1_address'], unique=False)
    op.create_index('ix_escrow_operations_participant2_address', 'escrow_operations', ['participant2_address'], unique=False)
    op.create_index('ix_escrow_participants', 'escrow_operations', ['blockchain', 'network', 'participant1_address', 'participant2_address'], unique=False)
    
    # For existing records, populate from address_roles JSONB (if any exist)
    # This migration assumes no existing data or manual data migration needed
    
    # Make columns not nullable after population
    op.alter_column('escrow_operations', 'participant1_address', nullable=False)
    op.alter_column('escrow_operations', 'participant2_address', nullable=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_escrow_participants', table_name='escrow_operations')
    op.drop_index('ix_escrow_operations_participant2_address', table_name='escrow_operations')
    op.drop_index('ix_escrow_operations_participant1_address', table_name='escrow_operations')
    
    # Drop columns
    op.drop_column('escrow_operations', 'participant2_address')
    op.drop_column('escrow_operations', 'participant1_address')

