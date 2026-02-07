"""
Модуль для авторизации через Web3 кошельки (MetaMask, TrustWallet, WalletConnect)
"""
import os
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException, status


class Web3Auth:
    """Класс для работы с Web3 авторизацией"""
    
    def __init__(self):
        # Секретный ключ для JWT (в продакшене использовать переменную окружения)
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24
        
        # Хранилище nonce для каждого адреса (в продакшене использовать БД)
        self.nonce_storage: Dict[str, str] = {}
    
    def generate_nonce(self, wallet_address: str) -> str:
        """
        Генерирует уникальный nonce для адреса кошелька
        
        Args:
            wallet_address: Адрес кошелька пользователя
            
        Returns:
            Сгенерированный nonce
        """
        # Генерируем случайный nonce
        nonce = secrets.token_hex(32)
        
        # Сохраняем nonce для данного адреса
        self.nonce_storage[wallet_address.lower()] = nonce
        
        return nonce
    
    def get_nonce(self, wallet_address: str) -> str:
        """
        Получает или генерирует nonce для адреса кошелька
        
        Args:
            wallet_address: Адрес кошелька пользователя
            
        Returns:
            Nonce для подписи
        """
        wallet_address_lower = wallet_address.lower()
        
        # Если nonce уже существует, возвращаем его
        if wallet_address_lower in self.nonce_storage:
            return self.nonce_storage[wallet_address_lower]
        
        # Иначе генерируем новый
        return self.generate_nonce(wallet_address)
    
    def verify_signature(
        self, 
        wallet_address: str, 
        signature: str, 
        message: Optional[str] = None
    ) -> bool:
        """
        Проверяет подпись от кошелька
        
        Args:
            wallet_address: Адрес кошелька
            signature: Подпись в hex формате
            message: Сообщение для проверки (если не указано, используется nonce)
            
        Returns:
            True если подпись валидна, иначе False
        """
        wallet_address_lower = wallet_address.lower()
        
        # Получаем nonce для данного адреса
        if wallet_address_lower not in self.nonce_storage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nonce not found. Please request a nonce first."
            )
        
        nonce = self.nonce_storage[wallet_address_lower]
        
        # Формируем сообщение для проверки
        if message is None:
            message = f"Please sign this message to authenticate:\n\nNonce: {nonce}"
        
        try:
            # Кодируем сообщение в формат, который понимает Ethereum
            message_encoded = encode_defunct(text=message)
            
            # Восстанавливаем адрес из подписи
            recovered_address = Account.recover_message(message_encoded, signature=signature)
            
            # Проверяем, что восстановленный адрес совпадает с переданным
            if recovered_address.lower() == wallet_address_lower:
                # Удаляем использованный nonce
                del self.nonce_storage[wallet_address_lower]
                return True
            
            return False
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid signature format: {str(e)}"
            )
    
    def generate_jwt_token(self, wallet_address: str) -> str:
        """
        Генерирует JWT токен для авторизованного пользователя
        
        Args:
            wallet_address: Адрес кошелька пользователя
            
        Returns:
            JWT токен
        """
        payload = {
            "wallet_address": wallet_address.lower(),
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
web3_auth = Web3Auth()

