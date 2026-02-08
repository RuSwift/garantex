"""
Модуль для авторизации через TRON кошельки (TronLink, TrustWallet, WalletConnect)
"""
import os
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, status
from tronpy import Tron
from tronpy.keys import PrivateKey


class TronAuth:
    """Класс для работы с TRON авторизацией"""
    
    def __init__(self):
        # Секретный ключ для JWT (в продакшене использовать переменную окружения)
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24
        
        # Хранилище nonce для каждого адреса (в продакшене использовать БД)
        self.nonce_storage: Dict[str, str] = {}
        
        # Инициализация TRON клиента (используем mainnet)
        self.tron = Tron()
    
    @staticmethod
    def validate_tron_address(address: str) -> bool:
        """
        Валидирует TRON адрес в формате base58
        
        Args:
            address: TRON адрес для валидации
            
        Returns:
            True если адрес валиден, иначе False
        """
        # TRON адреса начинаются с 'T' и имеют длину 34 символа
        if not address or not isinstance(address, str):
            return False
        
        if not address.startswith('T'):
            return False
        
        if len(address) != 34:
            return False
        
        # Проверяем, что адрес содержит только base58 символы
        base58_chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        if not all(c in base58_chars for c in address):
            return False
        
        return True
    
    def generate_nonce(self, wallet_address: str) -> str:
        """
        Генерирует уникальный nonce для адреса кошелька
        
        Args:
            wallet_address: TRON адрес кошелька пользователя
            
        Returns:
            Сгенерированный nonce
        """
        # Генерируем случайный nonce
        nonce = secrets.token_hex(32)
        
        # Сохраняем nonce для данного адреса (TRON адреса регистрозависимы)
        self.nonce_storage[wallet_address] = nonce
        
        return nonce
    
    def get_nonce(self, wallet_address: str) -> str:
        """
        Получает или генерирует nonce для адреса кошелька
        
        Args:
            wallet_address: TRON адрес кошелька пользователя
            
        Returns:
            Nonce для подписи
        """
        # Если nonce уже существует, возвращаем его
        if wallet_address in self.nonce_storage:
            return self.nonce_storage[wallet_address]
        
        # Иначе генерируем новый
        return self.generate_nonce(wallet_address)
    
    def verify_signature(
        self, 
        wallet_address: str, 
        signature: str, 
        message: Optional[str] = None
    ) -> bool:
        """
        Проверяет подпись от TRON кошелька
        
        Args:
            wallet_address: TRON адрес кошелька
            signature: Подпись в hex формате
            message: Сообщение для проверки (если не указано, используется nonce)
            
        Returns:
            True если подпись валидна, иначе False
        """
        # Получаем nonce для данного адреса
        if wallet_address not in self.nonce_storage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nonce not found. Please request a nonce first."
            )
        
        nonce = self.nonce_storage[wallet_address]
        
        # Формируем сообщение для проверки
        if message is None:
            message = f"Please sign this message to authenticate:\n\nNonce: {nonce}"
        
        try:
            # signMessageV2 в TronLink автоматически добавляет TRON-префикс
            # Формат: "\x19TRON Signed Message:\n" + len(message) + message
            tron_prefix = "\x19TRON Signed Message:\n"
            full_message = tron_prefix + str(len(message)) + message
            
            # Преобразуем сообщение в байты
            message_bytes = full_message.encode('utf-8')
            
            # Удаляем '0x' префикс из подписи если он есть
            if signature.startswith('0x'):
                signature = signature[2:]
            
            # Конвертируем hex подпись в байты
            signature_bytes = bytes.fromhex(signature)
            
            # Отладочный вывод
            print(f"Verifying TRON signature:")
            print(f"  Address: {wallet_address}")
            print(f"  Message: {message}")
            print(f"  Full message: {full_message}")
            print(f"  Signature length: {len(signature_bytes)}")
            
            # Проверяем подпись через tronpy
            # TronWeb на фронте подписывает сообщение, мы должны восстановить адрес
            from tronpy.keys import Signature
            from Crypto.Hash import keccak
            
            # Хешируем сообщение
            k = keccak.new(digest_bits=256)
            k.update(message_bytes)
            message_hash = k.digest()
            
            # Восстанавливаем публичный ключ из подписи
            # signature_bytes содержит r, s, v (65 байт)
            if len(signature_bytes) != 65:
                return False
            
            r = int.from_bytes(signature_bytes[:32], 'big')
            s = int.from_bytes(signature_bytes[32:64], 'big')
            v = signature_bytes[64]
            
            # Нормализуем v (TRON использует 27 или 28)
            # eth_keys ожидает v в диапазоне 0-3 (recovery_id)
            if v >= 27:
                v -= 27  # Конвертируем 27/28 в 0/1
            
            # Восстанавливаем публичный ключ
            from eth_keys import keys
            from eth_utils import keccak as eth_keccak
            
            # Используем vrs формат для создания подписи
            # eth_keys.Signature.from_vrs принимает отдельные параметры
            sig = keys.Signature(vrs=(v, r, s))
            
            # Восстанавливаем публичный ключ
            public_key = sig.recover_public_key_from_msg_hash(message_hash)
            
            # Получаем Ethereum-style адрес из публичного ключа
            pub_key_bytes = public_key.to_bytes()
            eth_address_bytes = eth_keccak(pub_key_bytes)[-20:]
            
            # Конвертируем в TRON адрес (добавляем префикс 0x41 и используем base58)
            tron_address_hex = '41' + eth_address_bytes.hex()
            
            # Конвертируем hex в base58 TRON адрес
            from tronpy.keys import to_base58check_address
            recovered_address = to_base58check_address(tron_address_hex)
            
            # Проверяем, что восстановленный адрес совпадает с переданным
            if recovered_address == wallet_address:
                # Удаляем использованный nonce
                del self.nonce_storage[wallet_address]
                return True
            
            return False
            
        except Exception as e:
            # Логируем ошибку для отладки
            print(f"Signature verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid signature format: {str(e)}"
            )
    
    def generate_jwt_token(self, wallet_address: str) -> str:
        """
        Генерирует JWT токен для авторизованного пользователя
        
        Args:
            wallet_address: TRON адрес кошелька пользователя
            
        Returns:
            JWT токен
        """
        payload = {
            "wallet_address": wallet_address,
            "blockchain": "tron",
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def verify_jwt_token(self, token: str) -> Dict:
        """
        Проверяет и декодирует JWT токен
        
        Args:
            token: JWT токен
            
        Returns:
            Декодированный payload токена
            
        Raises:
            HTTPException: Если токен невалиден
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


# Создаем глобальный экземпляр
tron_auth = TronAuth()


