"""add_avatar_and_unique_nickname

Revision ID: 65c2e0ae79f7
Revises: 012_access_to_admin_panel
Create Date: 2026-02-08 01:11:07.134796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65c2e0ae79f7'
down_revision: Union[str, None] = '012_access_to_admin_panel'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поле avatar для хранения изображения профиля
    op.add_column('wallet_users', sa.Column('avatar', sa.Text(), nullable=True, comment='User avatar in base64 format (data:image/...)'))
    
    # Создаем уникальный индекс на nickname (если его еще нет)
    op.create_index('uq_wallet_users_nickname', 'wallet_users', ['nickname'], unique=True)


def downgrade() -> None:
    # Удаляем уникальный индекс на nickname
    op.drop_index('uq_wallet_users_nickname', table_name='wallet_users')
    
    # Удаляем поле avatar
    op.drop_column('wallet_users', 'avatar')

