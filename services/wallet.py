"""
Wallet service для управления кошельками и шифрованием мнемоник
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from db.models import Wallet
from services.node import NodeService
from services.tron.utils import keypair_from_mnemonic
from didcomm.crypto import EthKeyPair, EthCrypto

logger = logging.getLogger(__name__)


class WalletService:
    """Сервис для управления кошельками"""
    
    @staticmethod
    def encrypt_mnemonic(mnemonic: str, secret: str) -> str:
        """
        Шифрует мнемоническую фразу
        
        Args:
            mnemonic: Мнемоническая фраза
            secret: Секретный ключ для шифрования
            
        Returns:
            Зашифрованная мнемоника
        """
        return NodeService.encrypt_data(mnemonic, secret)
    
    @staticmethod
    def decrypt_mnemonic(encrypted: str, secret: str) -> str:
        """
        Дешифрует мнемоническую фразу
        
        Args:
            encrypted: Зашифрованная мнемоника
            secret: Секретный ключ для дешифрования
            
        Returns:
            Расшифрованная мнемоника
        """
        return NodeService.decrypt_data(encrypted, secret)
    
    @staticmethod
    def generate_addresses_from_mnemonic(mnemonic: str) -> Dict[str, str]:
        """
        Генерирует адреса Tron и Ethereum из мнемонической фразы
        
        Args:
            mnemonic: Мнемоническая фраза
            
        Returns:
            Словарь с адресами: {'tron_address': str, 'ethereum_address': str}
            
        Raises:
            ValueError: Если мнемоническая фраза невалидна
        """
        # Валидируем мнемоническую фразу
        if not EthCrypto.validate_mnemonic(mnemonic):
            raise ValueError("Invalid mnemonic phrase")
        
        # Генерируем Tron адрес
        tron_address, _ = keypair_from_mnemonic(mnemonic, account_index=0)
        
        # Генерируем Ethereum адрес
        eth_keypair = EthKeyPair.from_mnemonic(mnemonic)
        ethereum_address = eth_keypair.address
        
        return {
            'tron_address': tron_address,
            'ethereum_address': ethereum_address
        }
    
    @staticmethod
    async def create_wallet(
        name: str,
        mnemonic: str,
        db: AsyncSession,
        secret: str
    ) -> Wallet:
        """
        Создает новый кошелек
        
        Args:
            name: Имя кошелька
            mnemonic: Мнемоническая фраза
            db: Database session
            secret: Секретный ключ для шифрования
            
        Returns:
            Созданный кошелек
            
        Raises:
            ValueError: Если мнемоника невалидна или адреса уже существуют
        """
        # Генерируем адреса
        addresses = WalletService.generate_addresses_from_mnemonic(mnemonic)
        
        # Проверяем, не существуют ли уже такие адреса
        result = await db.execute(
            select(Wallet).where(
                (Wallet.tron_address == addresses['tron_address']) |
                (Wallet.ethereum_address == addresses['ethereum_address'])
            )
        )
        existing_wallet = result.scalar_one_or_none()
        
        if existing_wallet:
            raise ValueError("Wallet with these addresses already exists")
        
        # Шифруем мнемоническую фразу
        encrypted_mnemonic = WalletService.encrypt_mnemonic(mnemonic, secret)
        
        # Создаем новый кошелек
        wallet = Wallet(
            name=name,
            encrypted_mnemonic=encrypted_mnemonic,
            tron_address=addresses['tron_address'],
            ethereum_address=addresses['ethereum_address']
        )
        
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        
        return wallet
    
    @staticmethod
    async def get_wallets(db: AsyncSession) -> List[Wallet]:
        """
        Получает список всех кошельков
        
        Args:
            db: Database session
            
        Returns:
            Список кошельков
        """
        result = await db.execute(select(Wallet).order_by(Wallet.created_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_wallet(wallet_id: int, db: AsyncSession) -> Optional[Wallet]:
        """
        Получает кошелек по ID
        
        Args:
            wallet_id: ID кошелька
            db: Database session
            
        Returns:
            Кошелек или None если не найден
        """
        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_wallet_name(
        wallet_id: int,
        name: str,
        db: AsyncSession
    ) -> Optional[Wallet]:
        """
        Обновляет имя кошелька
        
        Args:
            wallet_id: ID кошелька
            name: Новое имя
            db: Database session
            
        Returns:
            Обновленный кошелек или None если не найден
        """
        wallet = await WalletService.get_wallet(wallet_id, db)
        if not wallet:
            return None
        
        wallet.name = name
        await db.commit()
        await db.refresh(wallet)
        
        return wallet
    
    @staticmethod
    async def delete_wallet(wallet_id: int, db: AsyncSession) -> bool:
        """
        Удаляет кошелек
        
        Args:
            wallet_id: ID кошелька
            db: Database session
            
        Returns:
            True если кошелек удален, False если не найден
        """
        wallet = await WalletService.get_wallet(wallet_id, db)
        if not wallet:
            return False
        
        await db.execute(delete(Wallet).where(Wallet.id == wallet_id))
        await db.commit()
        
        return True

