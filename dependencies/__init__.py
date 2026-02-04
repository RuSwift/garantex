"""
Dependencies для FastAPI приложения
"""
from fastapi import Request, Depends
from typing import Optional
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from web3_auth import web3_auth

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


UserDepends = Annotated[Optional[dict], Depends(get_user_from_cookie)]


# Database dependency
DbDepends = Annotated[AsyncSession, Depends(get_db)]


# Экспортируем dependencies из модулей
__all__ = ["UserDepends", "SettingsDepends", "PrivKeyDepends", "DbDepends"]
