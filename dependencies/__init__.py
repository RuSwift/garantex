"""
Dependencies для FastAPI приложения
"""
from fastapi import Request, Depends, HTTPException, status
from typing import Optional
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from services.web3_auth import web3_auth
import jwt

# Импортируем dependencies из модулей
from dependencies.settings import SettingsDepends, PrivKeyDepends
from db import get_db


async def get_user_from_cookie(request: Request) -> Optional[dict]:
    """
    Dependency для получения информации о пользователе из cookie токена
    
    Возвращает словарь с wallet_address или None, если токен отсутствует или невалиден
    """
    token = request.cookies.get("auth_token")
    user_info = None
    
    if token:
        try:
            # Проверяем токен и получаем информацию о пользователе
            payload = web3_auth.verify_jwt_token(token)
            wallet_address = payload.get("wallet_address")
            if wallet_address:
                user_info = {"wallet_address": wallet_address}
        except Exception:
            # Если токен невалиден, игнорируем ошибку
            user_info = None
    
    return user_info


async def get_admin_from_cookie(
    request: Request,
    settings: SettingsDepends
) -> Optional[dict]:
    """
    Dependency для получения информации об админе из cookie токена
    
    Возвращает словарь с admin: True и дополнительной информацией, или None
    """
    token = request.cookies.get("admin_token")
    
    if not token:
        return None
    
    try:
        # Декодируем токен
        payload = jwt.decode(
            token,
            settings.secret.get_secret_value(),
            algorithms=["HS256"]
        )
        
        # Проверяем что это админский токен
        if payload.get("admin") is True:
            return {
                "admin": True,
                "username": payload.get("username"),
                "tron_address": payload.get("tron_address"),
                "blockchain": payload.get("blockchain")
            }
        
        return None
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


async def require_admin(
    request: Request,
    settings: SettingsDepends
) -> dict:
    """
    Dependency для требования админской авторизации
    
    Raises:
        HTTPException: Если пользователь не авторизован как админ
    """
    admin_info = await get_admin_from_cookie(request, settings)
    
    if not admin_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    
    return admin_info


UserDepends = Annotated[Optional[dict], Depends(get_user_from_cookie)]
AdminDepends = Annotated[Optional[dict], Depends(get_admin_from_cookie)]
RequireAdminDepends = Annotated[dict, Depends(require_admin)]


# Database dependency
DbDepends = Annotated[AsyncSession, Depends(get_db)]


# Экспортируем dependencies из модулей
__all__ = [
    "UserDepends", "AdminDepends", "RequireAdminDepends",
    "SettingsDepends", "PrivKeyDepends", "DbDepends"
]
