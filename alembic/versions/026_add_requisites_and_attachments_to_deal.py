"""Add requisites and attachments fields to deal table

Revision ID: 026_requisites_attachments_deal
Revises: 025_owner_did_escrow
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '026_requisites_attachments_deal'
down_revision: Union[str, None] = '025_owner_did_escrow'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add requisites column to deal table (JSONB for flexibility)
    op.add_column('deal', sa.Column('requisites', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Текущие реквизиты сделки (ФИО, назначение, валюта и др.)'))
    
    # Add attachments column to deal table (JSONB array of file references)
    op.add_column('deal', sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Ссылки на файлы в Storage (массив объектов с uuid, name, type и др.)'))
    
    # Create GIN indexes for efficient JSONB queries
    op.create_index('ix_deal_requisites', 'deal', ['requisites'], unique=False, postgresql_using='gin')
    op.create_index('ix_deal_attachments', 'deal', ['attachments'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_deal_attachments', table_name='deal', postgresql_using='gin')
    op.drop_index('ix_deal_requisites', table_name='deal', postgresql_using='gin')
    
    # Drop columns
    op.drop_column('deal', 'attachments')
    op.drop_column('deal', 'requisites')

