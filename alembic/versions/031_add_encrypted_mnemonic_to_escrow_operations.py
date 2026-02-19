"""Add encrypted_mnemonic field to escrow_operations table

Revision ID: 031_encrypted_mnemonic_escrow
Revises: 030_need_receiver_approve_deal
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '031_encrypted_mnemonic_escrow'
down_revision: Union[str, None] = '030_need_receiver_approve_deal'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Add encrypted_mnemonic column to escrow_operations table as nullable
    op.add_column(
        'escrow_operations',
        sa.Column(
            'encrypted_mnemonic',
            sa.Text(),
            nullable=True,
            comment='Encrypted mnemonic phrase for escrow (optional)'
        )
    )


def downgrade() -> None:
    # Drop encrypted_mnemonic column
    op.drop_column('escrow_operations', 'encrypted_mnemonic')

