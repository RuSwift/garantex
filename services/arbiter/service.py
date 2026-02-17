"""
Arbiter service для управления адресами арбитра
"""
import logging
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from db.models import Wallet
from services.node import NodeService
from services.wallet import WalletService

logger = logging.getLogger(__name__)


class ArbiterService:
    """Сервис для управления адресами арбитра"""
    
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
        return WalletService.generate_addresses_from_mnemonic(mnemonic)
    
    @staticmethod
    async def create_arbiter_address(
        mnemonic: str,
        name: str,
        db: AsyncSession,
        secret: str
    ) -> Wallet:
        """
        Создает адрес арбитра из мнемонической фразы
        
        Args:
            mnemonic: Мнемоническая фраза
            name: Имя адреса арбитра
            db: Database session
            secret: Секретный ключ для шифрования
            
        Returns:
            Созданный адрес арбитра (Wallet с role='arbiter')
            
        Raises:
            ValueError: Если мнемоника невалидна или адреса уже существуют
        """
        # Генерируем адреса
        addresses = ArbiterService.generate_addresses_from_mnemonic(mnemonic)
        
        # Проверяем, не существуют ли уже такие адреса среди арбитров
        result = await db.execute(
            select(Wallet).where(
                (Wallet.role == 'arbiter') &
                (
                    (Wallet.tron_address == addresses['tron_address']) |
                    (Wallet.ethereum_address == addresses['ethereum_address'])
                )
            )
        )
        existing_wallet = result.scalar_one_or_none()
        
        if existing_wallet:
            role_text = "арбитра" if existing_wallet.role == 'arbiter' else "кошелька"
            raise ValueError(
                f"Адрес уже существует как {role_text}. "
                f"TRON: {addresses['tron_address']}, "
                f"Ethereum: {addresses['ethereum_address']}"
            )
        
        # Находим существующий активный адрес арбитра (role='arbiter')
        # и меняем его роль на 'arbiter-backup'
        active_arbiter_result = await db.execute(
            select(Wallet).where(Wallet.role == 'arbiter')
        )
        active_arbiter = active_arbiter_result.scalar_one_or_none()
        
        if active_arbiter:
            active_arbiter.role = 'arbiter-backup'
            logger.info(
                "Changed existing arbiter role to backup: id=%d, name=%s",
                active_arbiter.id,
                active_arbiter.name
            )
        
        # Шифруем мнемоническую фразу
        encrypted_mnemonic = NodeService.encrypt_data(mnemonic, secret)
        
        # Создаем новый адрес арбитра
        wallet = Wallet(
            name=name,
            encrypted_mnemonic=encrypted_mnemonic,
            tron_address=addresses['tron_address'],
            ethereum_address=addresses['ethereum_address'],
            role='arbiter'
        )
        
        db.add(wallet)
        try:
            await db.commit()
            await db.refresh(wallet)
        except IntegrityError as e:
            await db.rollback()
            # Проверяем, какое именно ограничение нарушено
            # asyncpg оборачивает ошибку в e.orig
            error_str = ""
            if hasattr(e, 'orig'):
                error_str = str(e.orig)
            elif hasattr(e, 'args') and len(e.args) > 0:
                error_str = str(e.args[0])
            else:
                error_str = str(e)
            
            # Проверяем тип ошибки и поле
            if 'tron_address' in error_str.lower() or 'ix_wallets_tron_address' in error_str.lower():
                raise ValueError(
                    f"TRON адрес {addresses['tron_address']} уже существует в базе данных. "
                    f"Этот адрес уже используется другим кошельком."
                )
            elif 'ethereum_address' in error_str.lower() or 'ix_wallets_ethereum_address' in error_str.lower():
                raise ValueError(
                    f"Ethereum адрес {addresses['ethereum_address']} уже существует в базе данных. "
                    f"Этот адрес уже используется другим кошельком."
                )
            else:
                raise ValueError(
                    f"Адрес уже существует в базе данных. "
                    f"TRON: {addresses['tron_address']}, Ethereum: {addresses['ethereum_address']}"
                )
        
        logger.info(
            "Arbiter address created: id=%d, name=%s, tron_address=%s, ethereum_address=%s",
            wallet.id,
            wallet.name,
            wallet.tron_address,
            wallet.ethereum_address
        )
        
        return wallet
    
    @staticmethod
    async def get_arbiter_wallets(db: AsyncSession) -> List[Wallet]:
        """
        Получает список всех адресов арбитра из БД (включая активные и backup)
        
        Args:
            db: Database session
            
        Returns:
            Список адресов арбитра (Wallet с role='arbiter' или role='arbiter-backup')
        """
        result = await db.execute(
            select(Wallet)
            .where(
                (Wallet.role == 'arbiter') | (Wallet.role == 'arbiter-backup')
            )
            .order_by(Wallet.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_arbiter_wallet(wallet_id: int, db: AsyncSession) -> Optional[Wallet]:
        """
        Получает адрес арбитра по ID (активный или резервный)
        
        Args:
            wallet_id: ID адреса арбитра
            db: Database session
            
        Returns:
            Адрес арбитра или None если не найден
        """
        result = await db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .where(
                (Wallet.role == 'arbiter') | (Wallet.role == 'arbiter-backup')
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_arbiter_address_name(
        wallet_id: int,
        name: str,
        db: AsyncSession
    ) -> Optional[Wallet]:
        """
        Обновляет имя адреса арбитра
        
        Args:
            wallet_id: ID адреса арбитра
            name: Новое имя
            db: Database session
            
        Returns:
            Обновленный адрес арбитра или None если не найден
        """
        wallet = await ArbiterService.get_arbiter_wallet(wallet_id, db)
        if not wallet:
            return None
        
        wallet.name = name
        await db.commit()
        await db.refresh(wallet)
        
        return wallet
    
    @staticmethod
    async def delete_arbiter_address(wallet_id: int, db: AsyncSession) -> bool:
        """
        Удаляет адрес арбитра (активный или резервный)
        
        Args:
            wallet_id: ID адреса арбитра
            db: Database session
            
        Returns:
            True если адрес удален, False если не найден
        """
        wallet = await ArbiterService.get_arbiter_wallet(wallet_id, db)
        if not wallet:
            return False
        
        # Нельзя удалять активный адрес арбитра
        if wallet.role == 'arbiter':
            raise ValueError("Нельзя удалить активный адрес арбитра. Сначала активируйте другой адрес.")
        
        await db.execute(
            delete(Wallet)
            .where(Wallet.id == wallet_id)
            .where(
                (Wallet.role == 'arbiter') | (Wallet.role == 'arbiter-backup')
            )
        )
        await db.commit()
        
        logger.info("Arbiter address deleted: id=%d", wallet_id)
        
        return True
    
    @staticmethod
    async def switch_active_arbiter_address(
        wallet_id: int,
        db: AsyncSession
    ) -> Optional[Wallet]:
        """
        Переключает активный адрес арбитра
        
        Текущий активный адрес (role='arbiter') становится резервным (role='arbiter-backup'),
        а указанный резервный адрес становится активным (role='arbiter').
        
        Args:
            wallet_id: ID адреса арбитра, который нужно сделать активным (должен быть role='arbiter-backup')
            db: Database session
            
        Returns:
            Обновленный активный адрес арбитра или None если не найден или невалиден
            
        Raises:
            ValueError: Если адрес не найден, не является резервным, или нет активного адреса для переключения
        """
        # Получаем адрес, который нужно сделать активным
        wallet_to_activate = await ArbiterService.get_arbiter_wallet(wallet_id, db)
        if not wallet_to_activate:
            raise ValueError("Адрес арбитра не найден")
        
        # Проверяем, что адрес является резервным
        if wallet_to_activate.role != 'arbiter-backup':
            raise ValueError("Можно активировать только резервный адрес арбитра")
        
        # Находим текущий активный адрес
        active_result = await db.execute(
            select(Wallet).where(Wallet.role == 'arbiter')
        )
        active_wallet = active_result.scalar_one_or_none()
        
        if not active_wallet:
            raise ValueError("Не найден активный адрес арбитра для переключения")
        
        # Меняем роли местами
        active_wallet.role = 'arbiter-backup'
        wallet_to_activate.role = 'arbiter'
        
        await db.commit()
        await db.refresh(wallet_to_activate)
        await db.refresh(active_wallet)
        
        logger.info(
            "Switched active arbiter address: old_active_id=%d, new_active_id=%d",
            active_wallet.id,
            wallet_to_activate.id
        )
        
        return wallet_to_activate
    
    @staticmethod
    async def is_arbiter_initialized(db: AsyncSession) -> bool:
        """
        Проверяет, инициализирован ли арбитр
        
        Арбитр считается инициализированным, если есть хотя бы одна запись
        Wallet с role='arbiter'
        
        Args:
            db: Database session
            
        Returns:
            True если арбитр инициализирован, False иначе
        """
        result = await db.execute(
            select(Wallet).where(Wallet.role == 'arbiter').limit(1)
        )
        wallet = result.scalar_one_or_none()
        
        return wallet is not None
