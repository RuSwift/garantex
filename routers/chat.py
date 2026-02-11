"""
Router for ChatService API
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel

from routers.auth import get_current_tron_user, UserInfo
from dependencies import DbDepends
from services.chat.service import ChatService
from services.wallet_user import WalletUserService
from ledgers.chat.models import ChatMessage, ChatMessageCreate, ChatMessageResponse

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"]
)


def get_user_did(wallet_address: str, blockchain: str) -> str:
    """
    Формирует DID из wallet_address и blockchain
    
    Args:
        wallet_address: Адрес кошелька пользователя
        blockchain: Тип блокчейна (tron, ethereum, bitcoin, etc.)
        
    Returns:
        DID строка в формате did:{method}:{address}
    """
    blockchain_lower = blockchain.lower()
    
    if blockchain_lower in ['tron', 'ethereum', 'bitcoin']:
        # TRON, Ethereum, Bitcoin use secp256k1
        did_method = "ethr" if blockchain_lower == "ethereum" else blockchain_lower
        did = f"did:{did_method}:{wallet_address.lower()}"
    elif blockchain_lower in ['polkadot', 'substrate']:
        # Polkadot uses Ed25519
        did = f"did:polkadot:{wallet_address.lower()}"
    else:
        # Default to secp256k1 for unknown blockchains
        did = f"did:ethr:{wallet_address.lower()}"
    
    return did


async def get_chat_service(
    current_user: UserInfo = Depends(get_current_tron_user),
    db: DbDepends = None
) -> ChatService:
    """
    Dependency для создания ChatService с owner_did текущего пользователя
    
    Args:
        current_user: Текущий авторизованный пользователь
        db: Database session
        
    Returns:
        ChatService instance с настроенным owner_did
    """
    # Получаем пользователя из БД для получения blockchain
    user = await WalletUserService.get_by_wallet_address(current_user.wallet_address, db)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Формируем DID из wallet_address и blockchain
    owner_did = get_user_did(user.wallet_address, user.blockchain)
    
    # Создаем ChatService с owner_did
    return ChatService(session=db, owner_did=owner_did)


class AddMessageRequest(BaseModel):
    """Request для добавления сообщения"""
    message: ChatMessageCreate
    deal_uid: Optional[str] = None


class AddMessageResponse(BaseModel):
    """Response для добавления сообщения"""
    messages: List[ChatMessage]
    success: bool = True


@router.post("/messages", response_model=AddMessageResponse)
async def add_message(
    request: AddMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Добавить новое сообщение в чат
    
    Args:
        request: Данные сообщения
        chat_service: ChatService instance (автоматически создается с owner_did текущего пользователя)
        
    Returns:
        Список созданных сообщений
    """
    try:
        messages = await chat_service.add_message(
            message=request.message,
            deal_uid=request.deal_uid
        )
        
        return AddMessageResponse(
            messages=messages,
            success=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding message: {str(e)}"
        )


class GetHistoryResponse(BaseModel):
    """Response для получения истории сообщений"""
    messages: List[ChatMessage]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/history", response_model=GetHistoryResponse)
async def get_history(
    deal_uid: Optional[str] = Query(None, description="Filter by deal UID"),
    contact_id: Optional[str] = Query(None, description="Filter by contact ID"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of messages per page"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Получить историю сообщений с пагинацией
    
    Args:
        deal_uid: Фильтр по UID сделки (опционально)
        contact_id: Фильтр по ID контакта (опционально)
        page: Номер страницы (начиная с 1)
        page_size: Количество сообщений на странице
        chat_service: ChatService instance (автоматически создается с owner_did текущего пользователя)
        
    Returns:
        История сообщений с информацией о пагинации
    """
    try:
        result = await chat_service.get_history(
            deal_uid=deal_uid,
            contact_id=contact_id,
            page=page,
            page_size=page_size
        )
        
        return GetHistoryResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting history: {str(e)}"
        )


class SessionInfo(BaseModel):
    """Информация о сессии чата"""
    deal_uid: Optional[str]
    last_message_time: Optional[str]  # ISO format datetime
    message_count: int
    last_message: ChatMessage


class GetSessionsResponse(BaseModel):
    """Response для получения последних сессий"""
    sessions: List[SessionInfo]


@router.get("/sessions", response_model=GetSessionsResponse)
async def get_last_sessions(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Получить последние сессии чата, сгруппированные по deal_uid
    
    Args:
        limit: Максимальное количество сессий для возврата
        chat_service: ChatService instance (автоматически создается с owner_did текущего пользователя)
        
    Returns:
        Список последних сессий чата
    """
    try:
        sessions = await chat_service.get_last_sessions(limit=limit)
        
        # Преобразуем datetime в ISO строки
        session_list = []
        for session in sessions:
            session_list.append(SessionInfo(
                deal_uid=session["deal_uid"],
                last_message_time=session["last_message_time"].isoformat() if session["last_message_time"] else None,
                message_count=session["message_count"],
                last_message=session["last_message"]
            ))
        
        return GetSessionsResponse(sessions=session_list)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting sessions: {str(e)}"
        )

