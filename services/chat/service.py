"""
Service for managing chat messages and conversations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from uuid import uuid1

from db.models import Storage, Deal
from ledgers.chat.schemas import ChatMessage, ChatMessageCreate, FileAttachment


class ChatService:
    """Service for managing chat messages and conversations"""
    
    SPACE = "chat"
    
    def __init__(self, session: AsyncSession, owner_did: str):
        """
        Initialize chat service
        
        Args:
            session: Database async session
            owner_did: DID пользователя, которому принадлежит ledger (всегда фильтруется по этому полю)
        """
        self.session = session
        self.owner_did = owner_did
    
    async def add_message(
        self,
        message: ChatMessageCreate,
        deal_uid: Optional[str] = None
    ) -> List[ChatMessage]:
        """
        Add a new message to chat
        
        Args:
            message: Message to add (ChatMessageCreate)
            deal_uid: Deal UID if message is related to a deal (optional)
            
        Returns:
            List of created ChatMessage objects (one for each owner_did)
        """
        # Generate uuid for the message
        message_uuid = str(uuid1())
        
        # Create full ChatMessage from ChatMessageCreate
        # Note: conversation_id will be calculated per owner_did later
        full_message = ChatMessage(
            uuid=message_uuid,
            message_type=message.message_type,
            sender_id=message.sender_id,
            receiver_id=message.receiver_id,
            conversation_id=None,  # Будет рассчитан для каждого owner_did
            deal_uid=message.deal_uid,
            deal_label=message.deal_label,
            reply_to_message_uuid=message.reply_to_message_uuid,
            text=message.text,
            attachments=message.attachments,
            signature=message.signature,
            timestamp=datetime.now(timezone.utc),
            status="sent",
            metadata=message.metadata
        )
        
        # Convert message to dict for storage
        message_dict = full_message.model_dump()
        # Convert datetime objects to ISO format strings for JSON serialization
        if 'timestamp' in message_dict and isinstance(message_dict['timestamp'], datetime):
            message_dict['timestamp'] = message_dict['timestamp'].isoformat()
        if 'edited_at' in message_dict and message_dict['edited_at'] and isinstance(message_dict['edited_at'], datetime):
            message_dict['edited_at'] = message_dict['edited_at'].isoformat()
        if message_dict.get('signature') and 'signed_at' in message_dict['signature']:
            if isinstance(message_dict['signature']['signed_at'], datetime):
                message_dict['signature']['signed_at'] = message_dict['signature']['signed_at'].isoformat()
        
        # Determine owner_dids for storage records
        owner_dids: List[str] = []
        
        if deal_uid is None:
            # Если deal_uid = null, создаем 2 записи: для sender_id и receiver_id
            owner_dids = [message.sender_id, message.receiver_id]
        else:
            # Если deal_uid != null, загружаем Deal и создаем записи для всех participants
            deal = await self.session.execute(
                select(Deal).where(Deal.uid == deal_uid)
            )
            deal_obj = deal.scalar_one_or_none()
            
            if deal_obj:
                # Получаем всех участников из participants
                participants = deal_obj.participants
                if isinstance(participants, list) and len(participants) > 0:
                    owner_dids = list(participants)  # Все участники сделки
                else:
                    # Fallback: если participants пустой или не список, используем sender и receiver
                    owner_dids = [message.sender_id, message.receiver_id]
            else:
                # Если Deal не найден, используем sender и receiver
                owner_dids = [message.sender_id, message.receiver_id]
        
        # Убираем дубликаты и создаем записи для каждого owner_did
        owner_dids = list(set(owner_dids))  # Убираем дубликаты
        
        # Создаем storage records для каждого owner_did в одной транзакции (атомарно)
        created_messages = []
        try:
            for owner_did_value in owner_dids:
                # Рассчитываем conversation_id для каждого owner_did
                if deal_uid:
                    # Если сообщение связано со сделкой, conversation_id = deal_uid
                    conversation_id = deal_uid
                else:
                    # Иначе conversation_id = контрагент (тот, кто не является owner_did_value)
                    if owner_did_value == message.sender_id:
                        conversation_id = message.receiver_id
                    else:
                        conversation_id = message.sender_id
                
                # Обновляем conversation_id в message_dict для этого owner_did
                message_dict_copy = message_dict.copy()
                message_dict_copy['conversation_id'] = conversation_id
                
                storage = Storage(
                    space=self.SPACE,
                    deal_uid=deal_uid,
                    owner_did=owner_did_value,
                    conversation_id=conversation_id,
                    payload=message_dict_copy,
                    schema_ver="1"
                )
                self.session.add(storage)
                created_messages.append(full_message)
            
            # Коммитим транзакцию для гарантии атомарности
            await self.session.commit()
            
            return created_messages
        except Exception:
            # Откатываем транзакцию при ошибке
            await self.session.rollback()
            raise
    
    def _strip_file_data_from_message(self, message: ChatMessage, base_url: str = "/chat/api/attachment") -> Dict[str, Any]:
        """
        Удаляет поле data из attachments и добавляет download_url
        
        Args:
            message: Полное сообщение с файлами
            base_url: Базовый URL для загрузки файлов
            
        Returns:
            Словарь сообщения без file data
        """
        message_dict = message.model_dump()
        
        if message_dict.get('attachments'):
            for attachment in message_dict['attachments']:
                # Удаляем data
                if 'data' in attachment:
                    del attachment['data']
                
                # Добавляем URL для загрузки
                attachment['download_url'] = f"{base_url}/{message.uuid}/{attachment['id']}"
        
        return message_dict
    
    async def get_history(
        self,
        conversation_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        exclude_file_data: bool = False
    ) -> Dict[str, Any]:
        """
        Get chat history with pagination (always filtered by owner_did)
        
        Args:
            conversation_id: Filter by conversation ID (optional). If not specified, returns all messages.
            page: Page number (1-based)
            page_size: Number of messages per page
            exclude_file_data: If True, excludes file data from attachments (only metadata)
            
        Returns:
            Dictionary with 'messages' (list of ChatMessage) and 'total' (total count)
        """
        # Build query - всегда фильтруем по owner_did
        query = select(Storage).where(
            Storage.space == self.SPACE,
            Storage.owner_did == self.owner_did
        )
        
        # Filter by conversation_id
        if conversation_id:
            query = query.where(Storage.conversation_id == conversation_id)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering (oldest first for history)
        offset = (page - 1) * page_size
        query = query.order_by(Storage.id.asc()).offset(offset).limit(page_size)
        
        # Execute query
        result = await self.session.execute(query)
        storage_records = result.scalars().all()
        
        # Convert storage records to ChatMessage objects
        messages = []
        for storage in storage_records:
            try:
                payload = storage.payload
                # Convert ISO format strings back to datetime if needed
                if 'timestamp' in payload and isinstance(payload['timestamp'], str):
                    payload['timestamp'] = datetime.fromisoformat(payload['timestamp'].replace('Z', '+00:00'))
                if payload.get('edited_at') and isinstance(payload['edited_at'], str):
                    payload['edited_at'] = datetime.fromisoformat(payload['edited_at'].replace('Z', '+00:00'))
                if payload.get('signature') and 'signed_at' in payload['signature']:
                    if isinstance(payload['signature']['signed_at'], str):
                        payload['signature']['signed_at'] = datetime.fromisoformat(
                            payload['signature']['signed_at'].replace('Z', '+00:00')
                        )
                
                message = ChatMessage(**payload)
                
                # Если нужно исключить file data, преобразуем сообщение
                if exclude_file_data:
                    message_dict = self._strip_file_data_from_message(message)
                    messages.append(message_dict)
                else:
                    messages.append(message)
                    
            except Exception as e:
                # Skip invalid messages
                print(f"Error parsing message from storage {storage.id}: {e}")
                continue
        
        return {
            "messages": messages,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            "exclude_file_data": exclude_file_data
        }
    
    async def get_attachment(
        self,
        message_uuid: str,
        attachment_id: str
    ) -> Optional[FileAttachment]:
        """
        Get specific attachment with data
        
        Args:
            message_uuid: UUID сообщения
            attachment_id: ID вложения
            
        Returns:
            FileAttachment with data or None if not found
        """
        # Находим сообщение по UUID (owner_did проверяется для безопасности)
        query = select(Storage).where(
            Storage.space == self.SPACE,
            Storage.owner_did == self.owner_did,
            Storage.payload['uuid'].astext == message_uuid
        )
        
        result = await self.session.execute(query)
        storage = result.scalar_one_or_none()
        
        if not storage:
            return None
        
        # Парсим сообщение и ищем нужный attachment
        try:
            payload = storage.payload
            
            # Ищем нужный attachment
            attachments = payload.get('attachments', [])
            for att in attachments:
                if att.get('id') == attachment_id:
                    # Возвращаем полный attachment с data
                    return FileAttachment(**att)
            
            return None
            
        except Exception as e:
            print(f"Error getting attachment: {e}")
            return None
    
    async def get_last_sessions(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all last chat sessions grouped by conversation_id, sorted by time of last message
        (always filtered by owner_did)
        Optimized version using subquery with MAX(id)
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of dictionaries with session info:
            - conversation_id: Conversation ID (DID контрагента или deal_uid)
            - last_message_time: Time of last message in session
            - message_count: Number of messages in session
            - last_message: Last message in session (ChatMessage)
        """
        # Подзапрос: находим ID последнего сообщения для каждого conversation_id
        subquery = (
            select(
                Storage.conversation_id,
                func.max(Storage.id).label('last_id')
            )
            .where(
                Storage.space == self.SPACE,
                Storage.owner_did == self.owner_did
            )
            .group_by(Storage.conversation_id)
            .subquery()
        )
        
        # Основной запрос: получаем полные записи последних сообщений
        query = (
            select(Storage)
            .join(
                subquery,
                and_(
                    Storage.conversation_id == subquery.c.conversation_id,
                    Storage.id == subquery.c.last_id
                )
            )
            .order_by(desc(Storage.created_at))
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        sessions_list = result.scalars().all()
        
        # Build sessions list with full info
        sessions = []
        for storage in sessions_list:
            try:
                # Get message count for this conversation_id
                count_query = select(func.count(Storage.id)).where(
                    Storage.space == self.SPACE,
                    Storage.owner_did == self.owner_did
                )
                
                # Handle NULL conversation_id properly
                if storage.conversation_id is None:
                    count_query = count_query.where(Storage.conversation_id.is_(None))
                else:
                    count_query = count_query.where(Storage.conversation_id == storage.conversation_id)
                
                count_result = await self.session.execute(count_query)
                message_count = count_result.scalar() or 0
                
                # Parse last message
                payload = storage.payload
                # Convert ISO format strings back to datetime if needed
                if 'timestamp' in payload and isinstance(payload['timestamp'], str):
                    payload['timestamp'] = datetime.fromisoformat(payload['timestamp'].replace('Z', '+00:00'))
                if payload.get('edited_at') and isinstance(payload['edited_at'], str):
                    payload['edited_at'] = datetime.fromisoformat(payload['edited_at'].replace('Z', '+00:00'))
                if payload.get('signature') and 'signed_at' in payload['signature']:
                    if isinstance(payload['signature']['signed_at'], str):
                        payload['signature']['signed_at'] = datetime.fromisoformat(
                            payload['signature']['signed_at'].replace('Z', '+00:00')
                        )
                
                last_message = ChatMessage(**payload)
                
                sessions.append({
                    "conversation_id": storage.conversation_id,
                    "last_message_time": storage.created_at,
                    "message_count": message_count,
                    "last_message": last_message
                })
            except Exception as e:
                # Skip invalid sessions
                print(f"Error parsing session from storage {storage.id}: {e}")
                continue
        
        return sessions

