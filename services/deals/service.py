"""
Service for managing deals
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.dialects.postgresql import JSONB
import uuid

from db.models import Deal
from core.utils import generate_base58_uuid
from core.exceptions import DealAccessDeniedError
from services.chat.service import ChatService
from ledgers.chat.schemas import ChatMessageCreate, MessageType, FileAttachment


class DealsService:
    """Service for managing deals"""
    
    def __init__(self, session: AsyncSession, owner_did: str):
        """
        Initialize deals service
        
        Args:
            session: Database async session
            owner_did: DID пользователя, которому принадлежат сделки (sender_did)
                      Все операции фильтруются по этому полю (проверяется, что owner_did является участником: sender, receiver или arbiter)
        """
        self.session = session
        self.owner_did = owner_did
    
    def _is_participant(self, deal: Deal) -> bool:
        """
        Check if owner_did is a participant in the deal
        
        Args:
            deal: Deal object
            
        Returns:
            True if owner_did is sender, receiver or arbiter, False otherwise
        """
        return self.owner_did in [deal.sender_did, deal.receiver_did, deal.arbiter_did]
    
    def _is_deal_owner(self, deal: Deal) -> bool:
        """
        Check if current owner_did is the deal owner (sender_did)
        
        Args:
            deal: Deal object
            
        Returns:
            True if owner_did is the deal owner (sender_did), False otherwise
        """
        return deal.sender_did == self.owner_did
    
    def _check_deal_ownership(self, deal: Deal, deal_uid: str) -> None:
        """
        Check if current owner_did is the deal owner, raise exception if not
        
        Args:
            deal: Deal object
            deal_uid: Deal UID for error message
            
        Raises:
            DealAccessDeniedError: If owner_did is not the deal owner
        """
        if not self._is_deal_owner(deal):
            raise DealAccessDeniedError(
                deal_uid=deal_uid,
                owner_did=deal.sender_did,
                attempted_by=self.owner_did
            )
    
    async def create_deal(
        self,
        sender_did: str,
        receiver_did: str,
        arbiter_did: str,
        label: str,
        need_receiver_approve: bool = False
    ) -> Deal:
        """
        Create a new deal
        
        Args:
            sender_did: DID отправителя (owner сделки)
            receiver_did: DID получателя (тот, кто выставляет счет)
            arbiter_did: DID арбитра
            label: Описание сделки
            need_receiver_approve: Требуется ли одобрение получателя (default: False)
            
        Returns:
            Created Deal object
            
        Raises:
            ValueError: If owner_did is not a participant (sender, receiver or arbiter)
        """
        # Проверяем, что owner_did является участником сделки
        if self.owner_did not in [sender_did, receiver_did, arbiter_did]:
            raise ValueError(
                f"owner_did ({self.owner_did}) must be a participant "
                f"(sender_did, receiver_did or arbiter_did)"
            )
        
        # Генерируем base58 UUID для сделки
        deal_uid = generate_base58_uuid()
        
        # Создаем сделку
        deal = Deal(
            uid=deal_uid,
            sender_did=sender_did,
            receiver_did=receiver_did,
            arbiter_did=arbiter_did,
            label=label,
            need_receiver_approve=need_receiver_approve
        )
        
        self.session.add(deal)
        await self.session.commit()
        await self.session.refresh(deal)
        
        return deal
    
    async def get_deal(self, deal_uid: str) -> Optional[Deal]:
        """
        Get deal by UID (only if owner_did is a participant: sender, receiver or arbiter)
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            
        Returns:
            Deal object if found and owner_did is participant, None otherwise
        """
        # Загружаем сделку
        result = await self.session.execute(
            select(Deal).where(Deal.uid == deal_uid)
        )
        deal = result.scalar_one_or_none()
        
        if not deal:
            return None
        
        # Проверяем, что owner_did является участником сделки
        if not self._is_participant(deal):
            return None
        
        return deal
    
    async def get_deal_public(self, deal_uid: str) -> Optional[Deal]:
        """
        Get deal by UID (public access, no participant check)
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            
        Returns:
            Deal object if found, None otherwise
        """
        # Загружаем сделку
        result = await self.session.execute(
            select(Deal).where(Deal.uid == deal_uid)
        )
        deal = result.scalar_one_or_none()
        
        return deal
    
    async def list_deals(
        self,
        page: int = 1,
        page_size: int = 50,
        order_by: str = "created_at"
    ) -> Dict[str, Any]:
        """
        List deals where owner_did is a participant (sender, receiver or arbiter)
        
        Args:
            page: Page number (1-based)
            page_size: Number of deals per page
            order_by: Field to order by (created_at, updated_at)
            
        Returns:
            Dictionary with 'deals' (list of Deal) and 'total' (total count)
        """
        # Строим запрос - фильтруем по участникам (owner_did должен быть sender, receiver или arbiter)
        query = select(Deal).where(
            or_(
                Deal.sender_did == self.owner_did,
                Deal.receiver_did == self.owner_did,
                Deal.arbiter_did == self.owner_did
            )
        )
        
        # Получаем общее количество
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Применяем сортировку
        if order_by == "created_at":
            query = query.order_by(Deal.created_at.desc())
        elif order_by == "updated_at":
            query = query.order_by(Deal.updated_at.desc())
        else:
            query = query.order_by(Deal.created_at.desc())
        
        # Применяем пагинацию
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Выполняем запрос
        result = await self.session.execute(query)
        deals = result.scalars().all()
        
        return {
            "deals": list(deals),
            "total": total,
            "page": page,
            "page_size": page_size
        }
    
    async def update_deal(
        self,
        deal_uid: str,
        label: Optional[str] = None,
        sender_did: Optional[str] = None,
        receiver_did: Optional[str] = None,
        arbiter_did: Optional[str] = None,
        escrow_id: Optional[int] = None
    ) -> Optional[Deal]:
        """
        Update deal (only deal owner can edit)
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            label: New label (optional)
            sender_did: New sender DID (optional, must be current owner_did)
            receiver_did: New receiver DID (optional)
            arbiter_did: New arbiter DID (optional)
            escrow_id: New escrow ID (optional)
            
        Returns:
            Updated Deal object if found and owner_did is deal owner, None otherwise
            
        Raises:
            DealAccessDeniedError: If owner_did is not the deal owner
            ValueError: If sender_did is provided but doesn't match owner_did
        """
        # Загружаем сделку
        deal = await self.get_deal(deal_uid)
        
        if not deal:
            return None
        
        # Проверяем, что текущий пользователь - владелец сделки
        self._check_deal_ownership(deal, deal_uid)
        
        # Обновляем поля
        if label is not None:
            deal.label = label
        
        if sender_did is not None:
            # Проверяем, что sender_did совпадает с owner_did (владелец не может измениться)
            if sender_did != self.owner_did:
                raise ValueError(f"sender_did ({sender_did}) must match owner_did ({self.owner_did})")
            deal.sender_did = sender_did
        
        if receiver_did is not None:
            deal.receiver_did = receiver_did
        
        if arbiter_did is not None:
            deal.arbiter_did = arbiter_did
        
        if escrow_id is not None:
            deal.escrow_id = escrow_id
        
        # Обновляем updated_at
        deal.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(deal)
        
        return deal
    
    async def delete_deal(self, deal_uid: str) -> bool:
        """
        Delete deal (only deal owner can delete)
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            
        Returns:
            True if deal was deleted, False if not found
            
        Raises:
            DealAccessDeniedError: If owner_did is not the deal owner
        """
        # Загружаем сделку
        deal = await self.get_deal(deal_uid)
        
        if not deal:
            return False
        
        # Проверяем, что текущий пользователь - владелец сделки
        self._check_deal_ownership(deal, deal_uid)
        
        # Удаляем сделку
        await self.session.delete(deal)
        await self.session.commit()
        
        return True
    
    async def get_requisites(self, deal_uid: str) -> Optional[Dict[str, Any]]:
        """
        Get current requisites for a deal
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            
        Returns:
            Dictionary with requisites or None if deal not found
        """
        deal = await self.get_deal(deal_uid)
        
        if not deal:
            return None
        
        return deal.requisites if deal.requisites else {}
    
    async def update_requisites(
        self,
        deal_uid: str,
        requisites: Dict[str, Any],
        receiver_did: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update requisites for a deal (only deal owner can edit)
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            requisites: Dictionary with requisites (ФИО, назначение, валюта и др.)
            receiver_did: DID получателя для ChatMessage (optional, uses first other participant if not provided)
            
        Returns:
            Updated requisites dictionary or None if deal not found
            
        Raises:
            DealAccessDeniedError: If owner_did is not the deal owner
        """
        deal = await self.get_deal(deal_uid)
        
        if not deal:
            return None
        
        # Проверяем, что текущий пользователь - владелец сделки
        self._check_deal_ownership(deal, deal_uid)
        
        # Сохраняем старые реквизиты для истории
        old_requisites = deal.requisites if deal.requisites else {}
        
        # Обновляем реквизиты
        deal.requisites = requisites
        deal.updated_at = datetime.now(timezone.utc)
        
        # Определяем receiver_did для ChatMessage
        if receiver_did is None:
            # Используем receiver_did из сделки
            receiver_did = deal.receiver_did
        
        # Создаем ChatMessage для истории изменений
        chat_service = ChatService(self.session, self.owner_did)
        
        message_uuid = str(uuid.uuid4())
        message = ChatMessageCreate(
            uuid=message_uuid,
            message_type=MessageType.DEAL,
            sender_id=self.owner_did,
            receiver_id=receiver_did,
            deal_uid=deal_uid,
            deal_label=deal.label,
            text=f"Обновлены реквизиты сделки",
            metadata={
                "action": "update_requisites",
                "old_requisites": old_requisites,
                "new_requisites": requisites,
                "changed_by": self.owner_did
            }
        )
        
        # Сохраняем сообщение в историю
        await chat_service.add_message(message, deal_uid=deal_uid)
        
        # Коммитим изменения
        await self.session.commit()
        await self.session.refresh(deal)
        
        return deal.requisites
    
    async def get_attachments(self, deal_uid: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get current attachments for a deal
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            
        Returns:
            List of attachment dictionaries or None if deal not found
        """
        deal = await self.get_deal(deal_uid)
        
        if not deal:
            return None
        
        return deal.attachments if deal.attachments else []
    
    async def add_attachment(
        self,
        deal_uid: str,
        attachment: FileAttachment,
        receiver_did: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Add attachment to a deal (only deal owner can edit)
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            attachment: FileAttachment object with file data
            receiver_did: DID получателя для ChatMessage (optional, uses first other participant if not provided)
            
        Returns:
            Updated list of attachments or None if deal not found
            
        Raises:
            DealAccessDeniedError: If owner_did is not the deal owner
        """
        deal = await self.get_deal(deal_uid)
        
        if not deal:
            return None
        
        # Проверяем, что текущий пользователь - владелец сделки
        self._check_deal_ownership(deal, deal_uid)
        
        # Определяем receiver_did для ChatMessage
        if receiver_did is None:
            # Используем receiver_did из сделки
            receiver_did = deal.receiver_did
        
        # Создаем ChatService для сохранения файла
        chat_service = ChatService(self.session, self.owner_did)
        
        # Создаем ChatMessage с файлом
        message_uuid = str(uuid.uuid4())
        message = ChatMessageCreate(
            uuid=message_uuid,
            message_type=MessageType.FILE,
            sender_id=self.owner_did,
            receiver_id=receiver_did,
            deal_uid=deal_uid,
            deal_label=deal.label,
            attachments=[attachment]
        )
        
        # Сохраняем файл через ChatService (он сохранит в Storage)
        chat_message = await chat_service.add_message(message, deal_uid=deal_uid)
        
        # Получаем сохраненный файл из сообщения
        saved_attachment = None
        if chat_message.attachments and len(chat_message.attachments) > 0:
            saved_attachment = chat_message.attachments[0]
        
        if not saved_attachment:
            raise ValueError("Failed to save attachment")
        
        # Обновляем список attachments в Deal
        current_attachments = deal.attachments if deal.attachments else []
        
        # Создаем ссылку на файл (без data, только метаданные)
        # Используем message.uuid как идентификатор файла в Storage
        attachment_ref = {
            "message_uuid": message_uuid,  # UUID сообщения в Storage (используется для получения файла)
            "attachment_id": saved_attachment.id,  # ID вложения внутри сообщения
            "name": saved_attachment.name,
            "type": saved_attachment.type,
            "mime_type": saved_attachment.mime_type,
            "size": saved_attachment.size,
            "width": saved_attachment.width,
            "height": saved_attachment.height,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "added_by": self.owner_did
        }
        
        # Добавляем в список
        current_attachments.append(attachment_ref)
        deal.attachments = current_attachments
        deal.updated_at = datetime.now(timezone.utc)
        
        # Коммитим изменения
        await self.session.commit()
        await self.session.refresh(deal)
        
        return deal.attachments
    
    async def remove_attachment(
        self,
        deal_uid: str,
        attachment_uuid: str,
        receiver_did: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Remove attachment from a deal (only deal owner can edit)
        
        Args:
            deal_uid: Deal UID (base58 UUID)
            attachment_uuid: UUID of attachment to remove
            receiver_did: DID получателя для ChatMessage (optional, uses first other participant if not provided)
            
        Returns:
            Updated list of attachments or None if deal not found
            
        Raises:
            DealAccessDeniedError: If owner_did is not the deal owner
        """
        deal = await self.get_deal(deal_uid)
        
        if not deal:
            return None
        
        # Проверяем, что текущий пользователь - владелец сделки
        self._check_deal_ownership(deal, deal_uid)
        
        current_attachments = deal.attachments if deal.attachments else []
        
        # Находим и удаляем attachment
        # attachment_uuid может быть message_uuid или attachment_id
        removed_attachment = None
        updated_attachments = []
        for att in current_attachments:
            if att.get("message_uuid") == attachment_uuid or att.get("attachment_id") == attachment_uuid:
                removed_attachment = att
            else:
                updated_attachments.append(att)
        
        if not removed_attachment:
            # Attachment не найден
            return current_attachments
        
        # Определяем receiver_did для ChatMessage
        if receiver_did is None:
            # Используем receiver_did из сделки
            receiver_did = deal.receiver_did
        
        # Создаем ChatMessage для истории удаления
        chat_service = ChatService(self.session, self.owner_did)
        
        message_uuid = str(uuid.uuid4())
        message = ChatMessageCreate(
            uuid=message_uuid,
            message_type=MessageType.DEAL,
            sender_id=self.owner_did,
            receiver_id=receiver_did,
            deal_uid=deal_uid,
            deal_label=deal.label,
            text=f"Удален файл: {removed_attachment.get('name', 'unknown')}",
            metadata={
                "action": "remove_attachment",
                "removed_attachment": removed_attachment,
                "removed_by": self.owner_did
            }
        )
        
        # Сохраняем сообщение в историю
        await chat_service.add_message(message, deal_uid=deal_uid)
        
        # Обновляем список attachments
        deal.attachments = updated_attachments
        deal.updated_at = datetime.now(timezone.utc)
        
        # Коммитим изменения
        await self.session.commit()
        await self.session.refresh(deal)
        
        return deal.attachments

