"""add_did_column_to_wallet_users

Revision ID: 0b1d2be408bb
Revises: 024_conversation_id
Create Date: 2026-02-15 22:45:08.803310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b1d2be408bb'
down_revision: Union[str, None] = '024_conversation_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку did как nullable сначала
    op.add_column('wallet_users', 
        sa.Column('did', sa.String(300), nullable=True)
    )
    
    # Заполняем существующие записи
    from sqlalchemy import text
    connection = op.get_bind()
    
    # Импортируем функцию генерации DID
    import sys
    from pathlib import Path
    
    # Добавляем корневую папку проекта в sys.path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from core.utils import get_user_did
    
    # Получаем всех пользователей
    result = connection.execute(text("SELECT id, wallet_address, blockchain FROM wallet_users"))
    users = result.fetchall()
    
    # Обновляем DID для каждого пользователя
    for user_id, wallet_address, blockchain in users:
        did = get_user_did(wallet_address, blockchain)
        connection.execute(
            text("UPDATE wallet_users SET did = :did WHERE id = :user_id"),
            {"did": did, "user_id": user_id}
        )
    
    # Делаем колонку NOT NULL и добавляем UNIQUE constraint
    op.alter_column('wallet_users', 'did', nullable=False)
    op.create_unique_constraint('uq_wallet_users_did', 'wallet_users', ['did'])
    op.create_index('ix_wallet_users_did', 'wallet_users', ['did'])


def downgrade() -> None:
    op.drop_index('ix_wallet_users_did', 'wallet_users')
    op.drop_constraint('uq_wallet_users_did', 'wallet_users', type_='unique')
    op.drop_column('wallet_users', 'did')

