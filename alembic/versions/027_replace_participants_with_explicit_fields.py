"""Replace participants with explicit fields in deal table

Revision ID: 027_replace_participants_fields
Revises: 026_requisites_attachments_deal
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '027_replace_participants_fields'
down_revision: Union[str, None] = '026_requisites_attachments_deal'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Drop GIN index on participants
    op.drop_index('ix_deal_participants', table_name='deal', postgresql_using='gin')
    
    # Add new columns for explicit participant fields
    op.add_column('deal', sa.Column('sender_did', sa.String(length=255), nullable=True, comment='Sender DID (owner of the deal)'))
    op.add_column('deal', sa.Column('receiver_did', sa.String(length=255), nullable=True, comment='Receiver DID'))
    op.add_column('deal', sa.Column('arbiter_did', sa.String(length=255), nullable=True, comment='Arbiter DID'))
    op.add_column('deal', sa.Column('escrow_id', sa.BigInteger(), nullable=True, comment='Reference to escrow operation'))
    
    # Migrate data from participants JSONB to explicit fields
    # Note: This assumes participants is an array with [sender_did, receiver_did, arbiter_did]
    # If there are existing records, they need to be migrated
    op.execute("""
        UPDATE deal 
        SET 
            sender_did = (participants->>0)::text,
            receiver_did = (participants->>1)::text,
            arbiter_did = (participants->>2)::text
        WHERE participants IS NOT NULL 
        AND jsonb_array_length(participants) >= 3
    """)
    
    # Make columns NOT NULL after migration
    op.alter_column('deal', 'sender_did', nullable=False)
    op.alter_column('deal', 'receiver_did', nullable=False)
    op.alter_column('deal', 'arbiter_did', nullable=False)
    
    # Add foreign key constraint for escrow_id
    op.create_foreign_key(
        'fk_deal_escrow_id',
        'deal', 'escrow_operations',
        ['escrow_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes on new fields
    op.create_index('ix_deal_sender_did', 'deal', ['sender_did'], unique=False)
    op.create_index('ix_deal_receiver_did', 'deal', ['receiver_did'], unique=False)
    op.create_index('ix_deal_arbiter_did', 'deal', ['arbiter_did'], unique=False)
    op.create_index('ix_deal_escrow_id', 'deal', ['escrow_id'], unique=False)
    
    # Drop participants column
    op.drop_column('deal', 'participants')
    
    # Drop deals table (old unused table)
    op.drop_table('deals')


def downgrade() -> None:
    # Recreate deals table
    op.create_table(
        'deals',
        sa.Column('order_id', sa.BigInteger(), autoincrement=True, nullable=False, comment='Autoincrement primary key'),
        sa.Column('sender_did', sa.String(length=255), nullable=False, comment='Sender DID'),
        sa.Column('receiver_did', sa.String(length=255), nullable=False, comment='Receiver DID'),
        sa.Column('arbiter_did', sa.String(length=255), nullable=False, comment='Arbiter DID'),
        sa.Column('escrow_id', sa.BigInteger(), nullable=True, comment='Reference to escrow operation'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='Deal title'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp (UTC)'),
        sa.PrimaryKeyConstraint('order_id'),
        sa.ForeignKeyConstraint(['escrow_id'], ['escrow_operations.id'], ondelete='SET NULL')
    )
    
    # Recreate indexes for deals table
    op.create_index('ix_deals_order_id', 'deals', ['order_id'], unique=False)
    op.create_index('ix_deals_sender_did', 'deals', ['sender_did'], unique=False)
    op.create_index('ix_deals_receiver_did', 'deals', ['receiver_did'], unique=False)
    op.create_index('ix_deals_arbiter_did', 'deals', ['arbiter_did'], unique=False)
    op.create_index('ix_deals_escrow_id', 'deals', ['escrow_id'], unique=False)
    
    # Add participants column back
    op.add_column('deal', sa.Column('participants', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Array of participant DID identifiers'))
    
    # Migrate data back from explicit fields to participants
    op.execute("""
        UPDATE deal 
        SET participants = jsonb_build_array(sender_did, receiver_did, arbiter_did)
        WHERE sender_did IS NOT NULL 
        AND receiver_did IS NOT NULL 
        AND arbiter_did IS NOT NULL
    """)
    
    # Make participants NOT NULL
    op.alter_column('deal', 'participants', nullable=False)
    
    # Drop indexes on explicit fields
    op.drop_index('ix_deal_escrow_id', table_name='deal')
    op.drop_index('ix_deal_arbiter_did', table_name='deal')
    op.drop_index('ix_deal_receiver_did', table_name='deal')
    op.drop_index('ix_deal_sender_did', table_name='deal')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_deal_escrow_id', 'deal', type_='foreignkey')
    
    # Drop explicit field columns
    op.drop_column('deal', 'escrow_id')
    op.drop_column('deal', 'arbiter_did')
    op.drop_column('deal', 'receiver_did')
    op.drop_column('deal', 'sender_did')
    
    # Recreate GIN index on participants
    op.create_index('ix_deal_participants', 'deal', ['participants'], unique=False, postgresql_using='gin')

