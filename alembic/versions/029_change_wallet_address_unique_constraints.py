"""Change wallet address unique constraints to be role-based

Revision ID: 029_change_wallet_address_unique
Revises: 028_add_role_to_wallet
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '029_change_wallet_address_unique'
down_revision: Union[str, None] = '028_add_role_to_wallet'
branch_labels: Union[Sequence[str], str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Drop old unique indexes
    op.drop_index('ix_wallets_tron_address', table_name='wallets')
    op.drop_index('ix_wallets_ethereum_address', table_name='wallets')
    
    # Create new non-unique indexes for performance
    op.create_index('ix_wallets_tron_address', 'wallets', ['tron_address'], unique=False)
    op.create_index('ix_wallets_ethereum_address', 'wallets', ['ethereum_address'], unique=False)
    op.create_index('ix_wallets_role', 'wallets', ['role'], unique=False)
    
    # Create composite unique constraints (address + role)
    # Using UniqueConstraint from sqlalchemy
    op.create_unique_constraint(
        'uq_wallets_tron_address_role',
        'wallets',
        ['tron_address', 'role']
    )
    op.create_unique_constraint(
        'uq_wallets_ethereum_address_role',
        'wallets',
        ['ethereum_address', 'role']
    )


def downgrade() -> None:
    # Drop composite unique constraints
    op.drop_constraint('uq_wallets_ethereum_address_role', 'wallets', type_='unique')
    op.drop_constraint('uq_wallets_tron_address_role', 'wallets', type_='unique')
    
    # Drop new indexes
    op.drop_index('ix_wallets_role', table_name='wallets')
    op.drop_index('ix_wallets_ethereum_address', table_name='wallets')
    op.drop_index('ix_wallets_tron_address', table_name='wallets')
    
    # Restore old unique indexes
    op.create_index('ix_wallets_tron_address', 'wallets', ['tron_address'], unique=True)
    op.create_index('ix_wallets_ethereum_address', 'wallets', ['ethereum_address'], unique=True)

