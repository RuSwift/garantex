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
from ledgers.chat.schemas import ChatMessage, ChatMessageCreate, ChatMessageResponse
from ledgers import get_user_did

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


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


@router.post("/api/messages", response_model=AddMessageResponse)
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


@router.get("/api/history", response_model=GetHistoryResponse)
async def get_history(
    conversation_id: Optional[str] = Query(None, description="Filter by conversation ID"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of messages per page"),
    exclude_file_data: bool = Query(
        True,
        description="Exclude file data from attachments (recommended for performance). Use /api/attachment/{message_uuid}/{attachment_id} to download files."
    ),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Получить историю сообщений с пагинацией
    
    Args:
        conversation_id: Фильтр по ID беседы (опционально). Может быть DID контрагента или deal_uid.
        page: Номер страницы (начиная с 1)
        page_size: Количество сообщений на странице
        exclude_file_data: Исключить данные файлов из вложений (рекомендуется для производительности)
        chat_service: ChatService instance (автоматически создается с owner_did текущего пользователя)
        
    Returns:
        История сообщений с информацией о пагинации.
        Для загрузки файлов используйте /api/attachment/{message_uuid}/{attachment_id}
    """
    try:
        result = await chat_service.get_history(
            conversation_id=conversation_id,
            page=page,
            page_size=page_size,
            exclude_file_data=exclude_file_data
        )
        
        return GetHistoryResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting history: {str(e)}"
        )


@router.get("/api/attachment/{message_uuid}/{attachment_id}")
async def get_attachment(
    message_uuid: str,
    attachment_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Получить конкретное вложение с данными
    
    Args:
        message_uuid: UUID сообщения
        attachment_id: ID вложения
        
    Returns:
        FileAttachment with base64 data
    """
    try:
        attachment = await chat_service.get_attachment(message_uuid, attachment_id)
        
        if not attachment:
            raise HTTPException(
                status_code=404,
                detail="Attachment not found or access denied"
            )
        
        return attachment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting attachment: {str(e)}"
        )


class SessionInfo(BaseModel):
    """Информация о сессии чата"""
    conversation_id: Optional[str]
    last_message_time: Optional[str]  # ISO format datetime
    message_count: int
    last_message: ChatMessage


class GetSessionsResponse(BaseModel):
    """Response для получения последних сессий"""
    sessions: List[SessionInfo]


@router.get("/api/sessions", response_model=GetSessionsResponse)
async def get_last_sessions(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Получить последние сессии чата, сгруппированные по conversation_id
    
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
                conversation_id=session["conversation_id"],
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

