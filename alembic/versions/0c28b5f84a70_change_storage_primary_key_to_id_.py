"""change_storage_primary_key_to_id_bigserial

Revision ID: 0c28b5f84a70
Revises: 4fed365bf01f
Create Date: 2026-02-05 01:40:48.553019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0c28b5f84a70'
down_revision: Union[str, None] = '4fed365bf01f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create sequence for id column
    op.execute("CREATE SEQUENCE storage_id_seq")
    
    # Step 2: Add new id column as BIGINT with sequence as default
    # This allows existing rows to get values automatically
    op.add_column('storage', sa.Column('id', sa.BigInteger(), nullable=False, 
                                       server_default=sa.text("nextval('storage_id_seq')"),
                                       comment='Autoincrement primary key'))
    
    # Step 3: Set the sequence to be owned by the column (makes it a proper SERIAL)
    op.execute("ALTER SEQUENCE storage_id_seq OWNED BY storage.id")
    
    # Step 4: Drop the primary key constraint from uuid
    op.drop_constraint('storage_pkey', 'storage', type_='primary')
    
    # Step 5: Add unique constraint on uuid
    op.create_unique_constraint('uq_storage_uuid', 'storage', ['uuid'])
    
    # Step 6: Set id as the new primary key
    op.create_primary_key('storage_pkey', 'storage', ['id'])
    
    # Step 7: Create index on id (primary key already creates one, but explicit is better for consistency)
    # Note: If index already exists, this will fail - adjust manually if needed
    try:
        op.create_index('ix_storage_id', 'storage', ['id'], unique=False)
    except Exception:
        # Index might already exist, which is fine
        pass
    
    # Step 8: Ensure uuid has an index (it should already exist, but make sure)
    try:
        op.create_index('ix_storage_uuid', 'storage', ['uuid'], unique=False)
    except Exception:
        # Index might already exist, which is fine
        pass


def downgrade() -> None:
    # Step 1: Drop the primary key constraint from id
    op.drop_constraint('storage_pkey', 'storage', type_='primary')
    
    # Step 2: Drop unique constraint from uuid
    op.drop_constraint('uq_storage_uuid', 'storage', type_='unique')
    
    # Step 3: Drop indexes (if they exist)
    try:
        op.drop_index('ix_storage_uuid', table_name='storage')
    except Exception:
        pass
    try:
        op.drop_index('ix_storage_id', table_name='storage')
    except Exception:
        pass
    
    # Step 4: Drop the id column
    op.drop_column('storage', 'id')
    
    # Step 5: Drop the sequence
    op.execute("DROP SEQUENCE IF EXISTS storage_id_seq")
    
    # Step 6: Restore primary key on uuid
    op.create_primary_key('storage_pkey', 'storage', ['uuid'])

