"""
Utility functions for routers
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from db.models import WalletUser


def extract_protocol_name(message_type: str) -> Optional[str]:
    """
    Extract protocol name from DIDComm message type URI
    
    Example: "https://didcomm.org/trust-ping/1.0/ping" -> "trust-ping"
    
    Args:
        message_type: Full message type URI
        
    Returns:
        Protocol name or None
    """
    try:
        parts = message_type.split('/')
        if len(parts) >= 4:
            return parts[-3]  # protocol name is third from end
    except Exception:
        pass
    return None


async def get_wallet_address_by_did(did: str, db: AsyncSession) -> str:
    """
    Получить адрес кошелька по DID из БД пользователей
    
    Args:
        did: DID пользователя
        db: Database session
        
    Returns:
        Адрес кошелька пользователя
        
    Raises:
        HTTPException: Если пользователь не найден
    """
    if not did:
        raise HTTPException(
            status_code=400,
            detail="DID is required"
        )
    
    # Ищем пользователя по DID в БД
    result = await db.execute(
        select(WalletUser).where(WalletUser.did == did)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with DID '{did}' not found"
        )
    
    return user.wallet_address

