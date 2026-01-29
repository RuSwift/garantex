"""
Роутер для Web3 авторизации через кошельки (MetaMask, TrustWallet, WalletConnect)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional
from web3_auth import web3_auth

router = APIRouter(prefix="/auth", tags=["Авторизация"])

# Схемы для запросов
class NonceRequest(BaseModel):
    wallet_address: str = Field(..., description="Адрес кошелька пользователя")

class NonceResponse(BaseModel):
    nonce: str = Field(..., description="Nonce для подписи")
    message: str = Field(..., description="Сообщение для подписи")

class VerifyRequest(BaseModel):
    wallet_address: str = Field(..., description="Адрес кошелька пользователя")
    signature: str = Field(..., description="Подпись сообщения")
    message: Optional[str] = Field(None, description="Сообщение (опционально, если отличается от стандартного)")

class AuthResponse(BaseModel):
    token: str = Field(..., description="JWT токен для авторизации")
    wallet_address: str = Field(..., description="Адрес кошелька")

class UserInfo(BaseModel):
    wallet_address: str = Field(..., description="Адрес кошелька пользователя")

# Security scheme для JWT
security = HTTPBearer()


@router.post("/nonce", response_model=NonceResponse)
async def get_nonce(request: NonceRequest):
    """
    Получить nonce для авторизации через Web3 кошелек
    
    Поддерживаемые кошельки:
    - MetaMask
    - TrustWallet
    - WalletConnect
    
    Процесс авторизации:
    1. Вызовите этот endpoint с адресом кошелька
    2. Подпишите полученное сообщение в кошельке
    3. Отправьте подпись на /auth/verify
    """
    # Валидация адреса кошелька (базовая проверка формата)
    wallet_address = request.wallet_address.strip()
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid wallet address format"
        )
    
    # Получаем или генерируем nonce
    nonce = web3_auth.get_nonce(wallet_address)
    
    # Формируем сообщение для подписи
    message = f"Please sign this message to authenticate:\n\nNonce: {nonce}"
    
    return NonceResponse(nonce=nonce, message=message)


@router.post("/verify", response_model=AuthResponse)
async def verify_signature(request: VerifyRequest):
    """
    Проверить подпись и получить JWT токен
    
    После успешной проверки подписи возвращается JWT токен,
    который можно использовать для авторизации в защищенных эндпоинтах.
    """
    wallet_address = request.wallet_address.strip()
    
    # Валидация адреса
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid wallet address format"
        )
    
    # Проверяем подпись
    try:
        is_valid = web3_auth.verify_signature(
            wallet_address=wallet_address,
            signature=request.signature,
            message=request.message
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Генерируем JWT токен
        token = web3_auth.generate_jwt_token(wallet_address)
        
        return AuthResponse(token=token, wallet_address=wallet_address.lower())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during verification: {str(e)}"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInfo:
    """
    Dependency для получения текущего пользователя из JWT токена
    
    Используйте эту зависимость в других роутерах для защиты эндпоинтов:
    
    @router.get("/protected")
    async def protected_route(current_user: UserInfo = Depends(get_current_user)):
        return {"user": current_user.wallet_address}
    """
    token = credentials.credentials
    payload = web3_auth.verify_jwt_token(token)
    wallet_address = payload.get("wallet_address")
    
    if not wallet_address:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return UserInfo(wallet_address=wallet_address)


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: UserInfo = Depends(get_current_user)):
    """
    Получить информацию о текущем авторизованном пользователе
    
    Требует валидный JWT токен в заголовке Authorization: Bearer <token>
    """
    return current_user

