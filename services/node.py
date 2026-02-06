"""
Node service для инициализации и управления ключами ноды
"""
import json
import base64
import hashlib
from typing import Optional, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from db.models import NodeSettings
from didcomm.crypto import EthKeyPair, KeyPair, EthCrypto
from didcomm.did import create_peer_did_from_keypair
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class NodeService:
    """Сервис для управления инициализацией ноды и криптографическими ключами"""
    
    @staticmethod
    def _derive_encryption_key(secret: str) -> bytes:
        """
        Получает ключ шифрования из secret
        
        Args:
            secret: Секретный ключ из настроек
            
        Returns:
            32-байтовый ключ для AES-256
        """
        return hashlib.sha256(secret.encode('utf-8')).digest()
    
    @staticmethod
    def encrypt_data(plaintext: str, secret_key: str) -> str:
        """
        Шифрует данные через AES-GCM
        
        Args:
            plaintext: Открытый текст для шифрования
            secret_key: Секретный ключ из настроек
            
        Returns:
            Base64-encoded JSON строка с iv, tag и ciphertext
        """
        import secrets
        
        # Получаем ключ шифрования
        key = NodeService._derive_encryption_key(secret_key)
        
        # Генерируем IV
        iv = secrets.token_bytes(16)
        
        # Шифруем через AES-GCM
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
        tag = encryptor.tag
        
        # Формируем результат
        result = {
            "iv": base64.b64encode(iv).decode('utf-8'),
            "tag": base64.b64encode(tag).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
        }
        
        # Возвращаем в виде base64-encoded JSON
        return base64.b64encode(json.dumps(result).encode('utf-8')).decode('utf-8')
    
    @staticmethod
    def decrypt_data(encrypted: str, secret_key: str) -> str:
        """
        Дешифрует данные через AES-GCM
        
        Args:
            encrypted: Base64-encoded JSON строка с iv, tag и ciphertext
            secret_key: Секретный ключ из настроек
            
        Returns:
            Расшифрованный текст
        """
        # Получаем ключ шифрования
        key = NodeService._derive_encryption_key(secret_key)
        
        # Декодируем JSON
        data = json.loads(base64.b64decode(encrypted).decode('utf-8'))
        iv = base64.b64decode(data["iv"])
        tag = base64.b64decode(data["tag"])
        ciphertext = base64.b64decode(data["ciphertext"])
        
        # Дешифруем через AES-GCM
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext.decode('utf-8')
    
    @staticmethod
    async def init_from_mnemonic(
        mnemonic: str,
        db: AsyncSession,
        secret: str
    ) -> Dict[str, Any]:
        """
        Инициализирует ноду из мнемонической фразы
        
        Args:
            mnemonic: Мнемоническая фраза
            db: Database session
            secret: Секретный ключ для шифрования
            
        Returns:
            Информация о созданном ключе (DID, address, public_key, etc.)
            
        Raises:
            ValueError: Если мнемоническая фраза невалидна или нода уже инициализирована
        """
        # Проверяем, не инициализирована ли уже нода
        if await NodeService.is_node_initialized(db):
            raise ValueError("Нода инициализируется только один раз")
        
        # Валидируем мнемоническую фразу
        if not EthCrypto.validate_mnemonic(mnemonic):
            raise ValueError("Invalid mnemonic phrase")
        
        # Создаем keypair для проверки и получения адреса
        keypair = EthKeyPair.from_mnemonic(mnemonic)
        ethereum_address = keypair.address
        
        # Создаем DID
        did_obj = create_peer_did_from_keypair(keypair)
        
        # Шифруем мнемоническую фразу
        encrypted_mnemonic = NodeService.encrypt_data(mnemonic, secret)
        
        # Создаем новую запись
        node_settings = NodeSettings(
            encrypted_mnemonic=encrypted_mnemonic,
            encrypted_pem=None,
            key_type='mnemonic',
            ethereum_address=ethereum_address,
            is_active=True
        )
        
        db.add(node_settings)
        await db.commit()
        await db.refresh(node_settings)
        
        # Возвращаем информацию о ключе
        return {
            "did": did_obj.did,
            "address": ethereum_address,
            "key_type": "mnemonic",
            "public_key": keypair.public_key.hex(),
            "did_document": did_obj.to_dict()
        }
    
    @staticmethod
    async def init_from_pem(
        pem_data: str,
        password: Optional[str],
        db: AsyncSession,
        secret: str
    ) -> Dict[str, Any]:
        """
        Инициализирует ноду из PEM ключа
        
        Args:
            pem_data: PEM данные ключа
            password: Пароль для расшифровки PEM (опционально)
            db: Database session
            secret: Секретный ключ для шифрования
            
        Returns:
            Информация о созданном ключе (DID, public_key, etc.)
            
        Raises:
            ValueError: Если PEM данные невалидны или нода уже инициализирована
        """
        # Проверяем, не инициализирована ли уже нода
        if await NodeService.is_node_initialized(db):
            raise ValueError("Нода инициализируется только один раз")
        
        # Проверяем что PEM содержит маркеры приватного ключа
        pem_upper = pem_data.upper()
        has_private_marker = (
            'BEGIN PRIVATE KEY' in pem_upper or 
            'BEGIN RSA PRIVATE KEY' in pem_upper or
            'BEGIN EC PRIVATE KEY' in pem_upper or
            'BEGIN ENCRYPTED PRIVATE KEY' in pem_upper
        )
        
        if not has_private_marker:
            raise ValueError(
                "PEM данные не содержат приватный ключ. "
                "Ожидается PRIVATE KEY, не PUBLIC KEY или CERTIFICATE"
            )
        
        # Создаем keypair для валидации
        password_bytes = password.encode('utf-8') if password else None
        try:
            keypair = KeyPair.from_pem(pem_data, password_bytes)
        except ValueError as e:
            raise ValueError(f"Невалидный PEM приватный ключ: {e}")
        
        # Создаем DID
        did_obj = create_peer_did_from_keypair(keypair)
        
        # Для non-Ethereum ключей адрес будет None
        ethereum_address = None
        if isinstance(keypair, EthKeyPair):
            ethereum_address = keypair.address
        
        # Шифруем PEM данные
        encrypted_pem = NodeService.encrypt_data(pem_data, secret)
        
        # Создаем новую запись
        node_settings = NodeSettings(
            encrypted_mnemonic=None,
            encrypted_pem=encrypted_pem,
            key_type='pem',
            ethereum_address=ethereum_address,
            is_active=True
        )
        
        db.add(node_settings)
        await db.commit()
        await db.refresh(node_settings)
        
        # Возвращаем информацию о ключе
        return {
            "did": did_obj.did,
            "address": ethereum_address,
            "key_type": "pem",
            "public_key": keypair.public_key.hex(),
            "did_document": did_obj.to_dict()
        }
    
    @staticmethod
    async def get_active_keypair(
        db: AsyncSession,
        secret: str
    ) -> Union[EthKeyPair, KeyPair, None]:
        """
        Получает активный keypair из базы данных
        
        Args:
            db: Database session
            secret: Секретный ключ для дешифрования
            
        Returns:
            EthKeyPair, KeyPair или None если нода не инициализирована
        """
        # Ищем активную запись
        result = await db.execute(
            select(NodeSettings).where(NodeSettings.is_active == True)
        )
        node_settings = result.scalar_one_or_none()
        
        if not node_settings:
            return None
        
        # Дешифруем и создаем keypair в зависимости от типа
        if node_settings.key_type == 'mnemonic' and node_settings.encrypted_mnemonic:
            mnemonic = NodeService.decrypt_data(node_settings.encrypted_mnemonic, secret)
            return EthKeyPair.from_mnemonic(mnemonic)
        elif node_settings.key_type == 'pem' and node_settings.encrypted_pem:
            pem_data = NodeService.decrypt_data(node_settings.encrypted_pem, secret)
            return KeyPair.from_pem(pem_data)
        
        return None
    
    @staticmethod
    async def is_node_initialized(db: AsyncSession) -> bool:
        """
        Проверяет, инициализирована ли нода
        
        Args:
            db: Database session
            
        Returns:
            True если нода инициализирована, False иначе
        """
        result = await db.execute(
            select(NodeSettings).where(NodeSettings.is_active == True)
        )
        return result.scalar_one_or_none() is not None

