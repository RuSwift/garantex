"""
Роутер для Web3 авторизации через кошельки (MetaMask, TrustWallet, WalletConnect)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from services.web3_auth import web3_auth
from services.tron_auth import tron_auth
from services.wallet_user import WalletUserService
from db import get_db

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
async def verify_signature(request: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Проверить подпись и получить JWT токен
    
    После успешной проверки подписи возвращается JWT токен,
    который можно использовать для авторизации в защищенных эндпоинтах.
    """
    wallet_address = request.wallet_address.strip().lower()
    
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
        
        # Создаем или получаем пользователя в БД
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            # Создаем нового пользователя при первой авторизации
            # Генерируем nickname из адреса (первые 6 символов)
            nickname = f"User_{wallet_address[:8]}"
            
            try:
                user = await WalletUserService.create_user(
                    wallet_address=wallet_address,
                    blockchain="ethereum",
                    nickname=nickname,
                    db=db
                )
                print(f"✅ Created new Ethereum user: {wallet_address} (nickname: {nickname})")
            except ValueError as e:
                # Пользователь уже существует (race condition)
                print(f"⚠️ User creation failed (already exists): {e}")
                user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        else:
            print(f"✅ Existing Ethereum user logged in: {wallet_address}")
        
        # Генерируем JWT токен
        token = web3_auth.generate_jwt_token(wallet_address)
        
        return AuthResponse(token=token, wallet_address=wallet_address)
        
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


# ============================================================================
# TRON Authentication Endpoints
# ============================================================================

@router.post("/tron/nonce", response_model=NonceResponse)
async def get_tron_nonce(request: NonceRequest):
    """
    Получить nonce для авторизации через TRON кошелек
    
    Поддерживаемые кошельки:
    - TronLink
    - TrustWallet
    - WalletConnect
    
    Процесс авторизации:
    1. Вызовите этот endpoint с TRON адресом кошелька
    2. Подпишите полученное сообщение в кошельке
    3. Отправьте подпись на /auth/tron/verify
    """
    # Валидация TRON адреса (base58 формат)
    wallet_address = request.wallet_address.strip()
    if not tron_auth.validate_tron_address(wallet_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TRON address format. Address must start with 'T' and be 34 characters long."
        )
    
    # Получаем или генерируем nonce
    nonce = tron_auth.get_nonce(wallet_address)
    
    # Формируем сообщение для подписи
    message = f"Please sign this message to authenticate:\n\nNonce: {nonce}"
    
    return NonceResponse(nonce=nonce, message=message)


@router.post("/tron/verify", response_model=AuthResponse)
async def verify_tron_signature(request: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Проверить TRON подпись и получить JWT токен
    
    После успешной проверки подписи возвращается JWT токен,
    который можно использовать для авторизации в защищенных эндпоинтах.
    """
    wallet_address = request.wallet_address.strip()
    
    # Валидация TRON адреса
    if not tron_auth.validate_tron_address(wallet_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TRON address format"
        )
    
    # Проверяем подпись
    try:
        is_valid = tron_auth.verify_signature(
            wallet_address=wallet_address,
            signature=request.signature,
            message=request.message
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Создаем или получаем пользователя в БД
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            # Создаем нового пользователя при первой авторизации
            # Генерируем nickname из адреса (первые 6 символов)
            nickname = f"User_{wallet_address[:6]}"
            
            try:
                user = await WalletUserService.create_user(
                    wallet_address=wallet_address,
                    blockchain="tron",
                    nickname=nickname,
                    db=db
                )
                print(f"✅ Created new TRON user: {wallet_address} (nickname: {nickname})")
            except ValueError as e:
                # Пользователь уже существует (race condition)
                print(f"⚠️ User creation failed (already exists): {e}")
                user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        else:
            print(f"✅ Existing TRON user logged in: {wallet_address}")
        
        # Генерируем JWT токен
        token = tron_auth.generate_jwt_token(wallet_address)
        
        return AuthResponse(token=token, wallet_address=wallet_address)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during verification: {str(e)}"
        )


async def get_current_tron_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInfo:
    """
    Dependency для получения текущего TRON пользователя из JWT токена
    """
    token = credentials.credentials
    payload = tron_auth.verify_jwt_token(token)
    wallet_address = payload.get("wallet_address")
    
    if not wallet_address:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Проверяем, что это TRON токен
    if payload.get("blockchain") != "tron":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: not a TRON token"
        )
    
    return UserInfo(wallet_address=wallet_address)


@router.get("/tron/me", response_model=UserInfo)
async def get_current_tron_user_info(current_user: UserInfo = Depends(get_current_tron_user)):
    """
    Получить информацию о текущем авторизованном TRON пользователе
    
    Требует валидный JWT токен в заголовке Authorization: Bearer <token>
    """
    return current_user

