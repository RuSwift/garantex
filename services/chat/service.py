"""
Service for managing chat messages and conversations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from uuid import uuid1

from db.models import Storage, Deal
from ledgers.chat.models import ChatMessage, ChatMessageCreate


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
        # Generate id and uuid for the message
        message_uuid = str(uuid1())
        message_id = f"msg-{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Create full ChatMessage from ChatMessageCreate
        full_message = ChatMessage(
            id=message_id,
            uuid=message_uuid,
            message_type=message.message_type,
            sender_id=message.sender_id,
            receiver_id=message.receiver_id,
            contact_id=message.contact_id,
            deal_id=message.deal_id,
            deal_uid=message.deal_uid,
            deal_label=message.deal_label,
            reply_to_message_uuid=message.reply_to_message_uuid,
            text=message.text,
            attachments=message.attachments,
            signature=message.signature,
            timestamp=datetime.utcnow(),
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
                storage = Storage(
                    space=self.SPACE,
                    deal_uid=deal_uid or message.deal_uid,
                    owner_did=owner_did_value,
                    payload=message_dict,
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
    
    async def get_history(
        self,
        deal_uid: Optional[str] = None,
        contact_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Get chat history with pagination (always filtered by owner_did)
        
        Args:
            deal_uid: Filter by deal UID (optional)
            contact_id: Filter by contact ID (optional)
            page: Page number (1-based)
            page_size: Number of messages per page
            
        Returns:
            Dictionary with 'messages' (list of ChatMessage) and 'total' (total count)
        """
        # Build query - всегда фильтруем по owner_did
        query = select(Storage).where(
            Storage.space == self.SPACE,
            Storage.owner_did == self.owner_did
        )
        
        # Apply filters
        if deal_uid is not None:
            query = query.where(Storage.deal_uid == deal_uid)
        else:
            # If no deal_uid specified, get messages without deal_uid
            query = query.where(Storage.deal_uid.is_(None))
        
        # Additional filters from payload (using JSONB operators)
        if contact_id:
            query = query.where(
                or_(
                    Storage.payload['sender_id'].astext == contact_id,
                    Storage.payload['receiver_id'].astext == contact_id
                )
            )
        
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
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }
    
    async def get_last_sessions(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all last chat sessions grouped by deal_uid, sorted by time of last message
        (always filtered by owner_did)
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of dictionaries with session info:
            - deal_uid: Deal UID (or None for general chats)
            - last_message_time: Time of last message in session
            - message_count: Number of messages in session
            - last_message: Last message in session (ChatMessage)
        """
        # Build base query - всегда фильтруем по owner_did
        base_query = select(Storage).where(
            Storage.space == self.SPACE,
            Storage.owner_did == self.owner_did
        )
        
        # Get all messages ordered by created_at descending
        all_messages_query = base_query.order_by(desc(Storage.created_at))
        result = await self.session.execute(all_messages_query)
        all_storage_records = result.scalars().all()
        
        # Group by deal_uid and get last message for each group
        sessions_dict: Dict[Optional[str], Storage] = {}
        for storage in all_storage_records:
            deal_uid = storage.deal_uid
            # If we haven't seen this deal_uid yet, or this message is newer, store it
            if deal_uid not in sessions_dict:
                sessions_dict[deal_uid] = storage
            elif storage.created_at > sessions_dict[deal_uid].created_at:
                sessions_dict[deal_uid] = storage
        
        # Convert to list and sort by last_message_time descending
        sessions_list = list(sessions_dict.values())
        sessions_list.sort(key=lambda x: x.created_at, reverse=True)
        
        # Limit results
        sessions_list = sessions_list[:limit]
        
        # Build sessions list with full info
        sessions = []
        for storage in sessions_list:
            try:
                # Get message count for this deal_uid
                count_query = select(func.count(Storage.id)).where(
                    Storage.space == self.SPACE,
                    Storage.owner_did == self.owner_did
                )
                
                # Handle NULL deal_uid properly
                if storage.deal_uid is None:
                    count_query = count_query.where(Storage.deal_uid.is_(None))
                else:
                    count_query = count_query.where(Storage.deal_uid == storage.deal_uid)
                
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
                    "deal_uid": storage.deal_uid,
                    "last_message_time": storage.created_at,
                    "message_count": message_count,
                    "last_message": last_message
                })
            except Exception as e:
                # Skip invalid sessions
                print(f"Error parsing session from storage {storage.id}: {e}")
                continue
        
        return sessions

