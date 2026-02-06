"""
Dependencies для работы с настройками ноды
"""
from settings import Settings
from typing import Union
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db

from didcomm.crypto import EthKeyPair, KeyPair


async def get_settings() -> Settings:
    return Settings()


SettingsDepends = Annotated[Settings, Depends(get_settings)]


async def get_node_priv_key(settings: SettingsDepends, db: AsyncSession = Depends(get_db)) -> Union[EthKeyPair, KeyPair, None]:
    """
    Получает приватный ключ ноды
    
    Приоритет: env vars > БД
    Если env vars установлены, они используются для чтения ключа,
    но БД при этом не перезатирается
    
    Args:
        settings: Настройки приложения
        db: Database session
        
    Returns:
        EthKeyPair, KeyPair или None если нода не инициализирована
    """
    # Импортируем здесь, чтобы избежать циклических импортов
    from services.node import NodeService
    
    # Приоритет: env vars > БД
    # Если env vars установлены, используем их (БД не трогаем)
    if settings.mnemonic.phrase:
        return EthKeyPair.from_mnemonic(settings.mnemonic.phrase.get_secret_value())
    elif settings.mnemonic.encrypted_phrase:
        return EthKeyPair.from_encrypted_mnemonic(settings.mnemonic.encrypted_phrase.get_secret_value())
    elif settings.pem:
        return KeyPair.from_pem(settings.pem)
    
    # Fallback на БД если env vars не установлены
    db_key = await NodeService.get_active_keypair(db, settings.secret.get_secret_value())
    if db_key is not None:
        return db_key
    
    return None


PrivKeyDepends = Annotated[Union[EthKeyPair, KeyPair, None], Depends(get_node_priv_key)]
