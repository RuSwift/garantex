"""
Service for managing deals
"""
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.dialects.postgresql import JSONB
import uuid

from fastapi import HTTPException

from db.models import Deal, EscrowModel, Storage, WalletUser

# Кеш проверки депозита: deal_uid -> (timestamp, confirmed). TTL 10 сек.
_deposit_check_cache: Dict[str, Tuple[float, bool]] = {}
DEPOSIT_CHECK_TTL_SEC = 10
from core.utils import generate_base58_uuid
from core.exceptions import DealAccessDeniedError
from services.chat.service import ChatService
from services.tron.escrow import EscrowService
from services.tron.constants import USDT_CONTRACT_MAINNET
from ledgers.chat.schemas import ChatMessageCreate, MessageType, FileAttachment

logger = logging.getLogger(__name__)


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
        need_receiver_approve: bool = False,
        escrow_id: Optional[int] = None,
        description: Optional[str] = None,
        amount: Optional[float] = None
    ) -> Deal:
        """
        Create a new deal
        
        Args:
            sender_did: DID отправителя (owner сделки)
            receiver_did: DID получателя (тот, кто выставляет счет)
            arbiter_did: DID арбитра
            label: Заголовок сделки
            need_receiver_approve: Требуется ли одобрение получателя (default: False)
            escrow_id: Optional escrow ID to link with the deal
            description: Опциональное описание сделки
            
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
            description=description,
            need_receiver_approve=need_receiver_approve,
            status='wait_deposit',
            escrow_id=escrow_id,
            amount=amount
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

    async def get_or_build_deal_payout_txn(self, deal_uid: str) -> Optional[Dict[str, Any]]:
        """
        Get or build the offline payout transaction for a deal based on its status.
        For tron escrow: builds multisig payout (escrow -> receiver/sender per status).
        Stores serializable payload in deal.payout_txn with signatures: [].
        """
        from routers.utils import get_wallet_address_by_did

        deal = await self.get_deal(deal_uid)
        if not deal:
            return None

        if not deal.escrow_id:
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None

        result = await self.session.execute(
            select(EscrowModel).where(EscrowModel.id == deal.escrow_id)
        )
        escrow = result.scalar_one_or_none()
        if not escrow or escrow.blockchain != "tron":
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None

        if deal.status == "wait_deposit":
            if not deal.deposit_txn_hash:
                deal.payout_txn = None
                deal.updated_at = datetime.now(timezone.utc)
                await self.session.commit()
                return None
            confirmed = await self._is_deposit_tx_confirmed(deal_uid, deal.deposit_txn_hash, escrow.network)
            if not confirmed:
                return None
            deal.status = "processing"
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(deal)
            # Сервисное сообщение о депозите — только если такого ещё нет (один раз на txn_hash)
            try:
                existing = await self.session.execute(
                    select(1)
                    .select_from(Storage)
                    .where(
                        Storage.space == "chat",
                        Storage.deal_uid == deal_uid,
                        Storage.payload["message_type"].astext == "service",
                        Storage.payload["txn_hash"].astext == (deal.deposit_txn_hash or ""),
                    )
                    .limit(1)
                )
                if existing.scalar() is None:
                    sender_user = (
                        await self.session.execute(select(WalletUser).where(WalletUser.did == deal.sender_did))
                    ).scalar_one_or_none()
                    nickname = sender_user.nickname if sender_user else deal.sender_did
                    service_text = f"{nickname} внёс депозит в эскроу."
                    chat_svc = ChatService(self.session, deal.sender_did)
                    deposit_message = ChatMessageCreate(
                        uuid=str(uuid.uuid4()),
                        message_type=MessageType.SERVICE,
                        sender_id=deal.sender_did,
                        receiver_id=deal.receiver_did,
                        deal_uid=deal.uid,
                        deal_label=deal.label,
                        text=service_text,
                        txn_hash=deal.deposit_txn_hash,
                    )
                    await chat_svc.add_message(deposit_message, deal_uid=deal.uid)
                    await self.session.commit()
            except Exception as e:
                logger.warning("get_or_build_deal_payout_txn: failed to add deposit service message for deal %s: %s", deal_uid, e)

        if deal.status in ("appeal", "wait_arbiter", "recline_appeal"):
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None

        if deal.status in ("processing", "success"):
            to_did = deal.receiver_did
        elif deal.status in ("resolving_sender", "resolved_sender"):
            to_did = deal.sender_did
        elif deal.status in ("resolving_receiver", "resolved_receiver"):
            to_did = deal.receiver_did
        else:
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None

        try:
            to_address = await get_wallet_address_by_did(to_did, self.session)
        except HTTPException as e:
            logger.warning("get_or_build_deal_payout_txn: user not found for to_did=%s: %s", to_did, e.detail)
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None

        # amount: из колонки deal.amount или из deal.requisites["amount"]
        amount = deal.amount
        requisites = deal.requisites or {}
        if amount is None:
            amount = requisites.get("amount")
        if amount is None:
            logger.info("get_or_build_deal_payout_txn: deal %s has no amount", deal_uid)
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None

        token_contract = requisites.get("token_contract") or USDT_CONTRACT_MAINNET

        # Reuse existing payload if it matches current status (to_address, amount, token) — no TronAPI call
        existing = deal.payout_txn
        if existing and isinstance(existing, dict):
            if (
                existing.get("to_address") == to_address
                and float(existing.get("amount") or 0) == amount
                and existing.get("token_contract") == token_contract
            ):
                # Для processing при двух подписях и наличии txID — перезапросить статус в сети; при success закрыть сделку
                if deal.status == "processing":
                    sigs = existing.get("signatures") or []
                    required = existing.get("required_signatures") or len(existing.get("participants") or [])
                    if len(sigs) >= required:
                        unsigned = existing.get("unsigned_tx")
                        tx_hash = (unsigned.get("txID") or "").strip() if isinstance(unsigned, dict) else None
                        if tx_hash and escrow:
                            try:
                                if await self._is_payout_tx_success(tx_hash, escrow.network):
                                    try:
                                        sender_user = (
                                            await self.session.execute(
                                                select(WalletUser).where(WalletUser.did == deal.sender_did)
                                            )
                                        ).scalar_one_or_none()
                                        nickname = sender_user.nickname if sender_user else deal.sender_did
                                        service_text = f"{nickname} {deal.sender_did} подтвердил и претензий не имеет"
                                        chat_svc = ChatService(self.session, deal.sender_did)
                                        service_message = ChatMessageCreate(
                                            uuid=str(uuid.uuid4()),
                                            message_type=MessageType.SERVICE,
                                            sender_id=deal.sender_did,
                                            receiver_id=deal.receiver_did,
                                            deal_uid=deal.uid,
                                            deal_label=deal.label,
                                            text=service_text,
                                            txn_hash=tx_hash,
                                        )
                                        await chat_svc.add_message(service_message, deal_uid=deal.uid)
                                    except Exception as e:
                                        logger.warning(
                                            "get_or_build_deal_payout_txn: failed to add completion service message for deal %s: %s",
                                            deal_uid,
                                            e,
                                        )
                                    deal.status = "success"
                                    deal.updated_at = datetime.now(timezone.utc)
                                    await self.session.commit()
                                    await self.session.refresh(deal)
                            except ValueError:
                                pass  # tx в сети ещё pending или failed
                return existing

        escrow_svc = EscrowService(self.session, deal.sender_did)
        try:
            create_result = await escrow_svc.create_payment_transaction(
                deal.escrow_id, to_address, amount, token_contract
            )
        except Exception as e:
            logger.warning("get_or_build_deal_payout_txn: create_payment_transaction failed for deal %s: %s", deal_uid, e)
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return None

        unsigned_tx = create_result["unsigned_tx"]
        if unsigned_tx.get("visible") is not True:
            unsigned_tx = {**unsigned_tx, "visible": True}
        contract_data = unsigned_tx.get("raw_data", {})
        contract_type = "TriggerSmartContract" if token_contract else "TransferContract"

        payload = {
            "blockchain": escrow.blockchain,
            "network": escrow.network,
            "escrow_id": deal.escrow_id,
            "to_address": to_address,
            "amount": amount,
            "token_contract": token_contract,
            "unsigned_tx": unsigned_tx,
            "contract_data": contract_data,
            "required_signatures": create_result["required_signatures"],
            "participants": create_result["participants"],
            "arbiter": create_result["arbiter"],
            "contract_type": contract_type,
            "signatures": [],
        }
        if create_result.get("owner_addresses"):
            payload["owner_addresses"] = create_result["owner_addresses"]

        deal.payout_txn = payload
        deal.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(deal)
        return payload

    async def refresh_deal_payout_txn(self, deal_uid: str) -> Optional[Dict[str, Any]]:
        """
        Clear existing payout_txn and rebuild it once via create_payment_transaction.
        Call after deal status changes so payload matches new to_address/amount/token.
        """
        deal = await self.get_deal(deal_uid)
        if not deal:
            return None
        deal.payout_txn = None
        await self.session.commit()
        await self.session.refresh(deal)
        return await self.get_or_build_deal_payout_txn(deal_uid)

    async def refresh_payout_txn_for_retry(
        self,
        deal_uid: str,
        failed_tx_hash: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Пересборка транзакции выплаты для повторной попытки (например после Out of Energy).
        Только отправитель, только при status=processing. Обнуляет подписи, создаёт новый unsigned_tx.
        Отправляет в чат сервисное сообщение о проблеме и пересборке.
        """
        deal = await self.get_deal(deal_uid)
        if not deal or self.owner_did != deal.sender_did:
            return None
        if deal.status != "processing":
            return None
        if deal.need_receiver_approve:
            return None
        new_payload = await self.refresh_deal_payout_txn(deal_uid)
        if not new_payload:
            return None
        reason_text = (reason or "").strip() or "транзакция не прошла в сети"
        failed_hash = (failed_tx_hash or "").strip() or None
        try:
            sender_user = (
                await self.session.execute(select(WalletUser).where(WalletUser.did == deal.sender_did))
            ).scalar_one_or_none()
            nickname = sender_user.nickname if sender_user else deal.sender_did
            parts = [
                f"{nickname} инициировал пересборку транзакции выплаты.",
                f"Причина: {reason_text}.",
                "Требуется повторная подпись получателя и отправителя.",
            ]
            if failed_hash:
                parts.insert(1, f"Проблемная транзакция: https://tronscan.org/#/transaction/{failed_hash}")
            service_text = " ".join(parts)
            chat_svc = ChatService(self.session, deal.sender_did)
            service_message = ChatMessageCreate(
                uuid=str(uuid.uuid4()),
                message_type=MessageType.SERVICE,
                sender_id=deal.sender_did,
                receiver_id=deal.receiver_did,
                deal_uid=deal.uid,
                deal_label=deal.label,
                text=service_text,
                txn_hash=failed_hash,
            )
            await chat_svc.add_message(service_message, deal_uid=deal.uid)
            await self.session.commit()
        except Exception as e:
            logger.warning("refresh_payout_txn_for_retry: failed to add service message for deal %s: %s", deal_uid, e)
        return new_payload

    async def set_deal_status(self, deal_uid: str, status: str) -> Optional[Deal]:
        """
        Update deal status and refresh payout_txn to match.
        Appeal states and final states: only arbiter can change. Appeal from processing: sender/receiver.
        """
        deal = await self.get_deal(deal_uid)
        if not deal:
            return None
        if deal.need_receiver_approve:
            raise ValueError("Deal not started: receiver approval required")
        appeal_statuses = ("wait_arbiter", "appeal", "recline_appeal", "resolving_sender", "resolving_receiver")
        final_statuses = ("success", "resolved_sender", "resolved_receiver")
        if deal.status in appeal_statuses or deal.status in final_statuses:
            if self.owner_did != deal.arbiter_did:
                raise ValueError("В состоянии апелляции или из финального статуса статус может менять только арбитр")

        if status == "appeal":
            if self.owner_did in (deal.sender_did, deal.receiver_did):
                if deal.status != "processing":
                    raise ValueError("Апелляция возможна только при статусе «В работе»")
                deal.status = "wait_arbiter"
                deal.payout_txn = None
                deal.updated_at = datetime.now(timezone.utc)
                await self.session.commit()
                try:
                    filer_user = (
                        await self.session.execute(select(WalletUser).where(WalletUser.did == self.owner_did))
                    ).scalar_one_or_none()
                    nickname = filer_user.nickname if filer_user else self.owner_did
                    service_text = f"{nickname} подал(а) на апелляцию"
                    other_did = deal.receiver_did if self.owner_did == deal.sender_did else deal.sender_did
                    chat_svc = ChatService(self.session, self.owner_did)
                    service_message = ChatMessageCreate(
                        uuid=str(uuid.uuid4()),
                        message_type=MessageType.SERVICE,
                        sender_id=self.owner_did,
                        receiver_id=other_did,
                        deal_uid=deal.uid,
                        deal_label=deal.label,
                        text=service_text,
                    )
                    await chat_svc.add_message(service_message, deal_uid=deal.uid)
                    await self.session.commit()
                except Exception as e:
                    logger.warning("set_deal_status appeal: failed to add service message for deal %s: %s", deal_uid, e)
                await self.refresh_deal_payout_txn(deal_uid)
                return await self.get_deal(deal_uid)
            elif self.owner_did == deal.arbiter_did:
                if deal.status not in final_statuses:
                    raise ValueError("Арбитр может вернуть в appeal только из финального статуса")
                deal.status = "wait_arbiter"
                deal.payout_txn = None
                deal.updated_at = datetime.now(timezone.utc)
                await self.session.commit()
                try:
                    chat_svc = ChatService(self.session, deal.arbiter_did)
                    service_message = ChatMessageCreate(
                        uuid=str(uuid.uuid4()),
                        message_type=MessageType.SERVICE,
                        sender_id=deal.arbiter_did,
                        receiver_id=deal.receiver_did,
                        deal_uid=deal.uid,
                        deal_label=deal.label,
                        text="Арбитр вернул сделку на пересмотр",
                    )
                    await chat_svc.add_message(service_message, deal_uid=deal.uid)
                    await self.session.commit()
                except Exception as e:
                    logger.warning("set_deal_status appeal arbiter: failed to add service message for deal %s: %s", deal_uid, e)
                await self.refresh_deal_payout_txn(deal_uid)
                return await self.get_deal(deal_uid)
            else:
                raise ValueError("Only sender, receiver or arbiter can set appeal")
        elif status in ("resolving_sender", "resolving_receiver"):
            if deal.status not in ("wait_arbiter", "appeal", "recline_appeal"):
                raise ValueError("Resolving only from wait_arbiter, appeal or recline_appeal")
            deal.status = status
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(deal)
            await self.refresh_deal_payout_txn(deal_uid)
            return await self.get_deal(deal_uid)
        elif status == "recline_appeal":
            if deal.status not in ("resolving_sender", "resolving_receiver"):
                raise ValueError("Recline only from resolving_sender or resolving_receiver")
            deal.status = "recline_appeal"
            deal.payout_txn = None
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            try:
                chat_svc = ChatService(self.session, deal.arbiter_did)
                service_message = ChatMessageCreate(
                    uuid=str(uuid.uuid4()),
                    message_type=MessageType.SERVICE,
                    sender_id=deal.arbiter_did,
                    receiver_id=deal.receiver_did,
                    deal_uid=deal.uid,
                    deal_label=deal.label,
                    text="Арбитр отправил заявку на пересмотр",
                )
                await chat_svc.add_message(service_message, deal_uid=deal.uid)
                await self.session.commit()
            except Exception as e:
                logger.warning("set_deal_status recline_appeal: failed to add service message for deal %s: %s", deal_uid, e)
            await self.refresh_deal_payout_txn(deal_uid)
            return await self.get_deal(deal_uid)
        elif status == "processing":
            if self.owner_did != deal.arbiter_did:
                raise ValueError("Only arbiter can return deal to processing")
            if deal.status in appeal_statuses or deal.status in final_statuses:
                deal.payout_txn = None
            deal.status = "processing"
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            try:
                chat_svc = ChatService(self.session, deal.arbiter_did)
                service_message = ChatMessageCreate(
                    uuid=str(uuid.uuid4()),
                    message_type=MessageType.SERVICE,
                    sender_id=deal.arbiter_did,
                    receiver_id=deal.receiver_did,
                    deal_uid=deal.uid,
                    deal_label=deal.label,
                    text="Арбитр вернул сделку в работу",
                )
                await chat_svc.add_message(service_message, deal_uid=deal.uid)
                await self.session.commit()
            except Exception as e:
                logger.warning("set_deal_status processing: failed to add service message for deal %s: %s", deal_uid, e)
            await self.refresh_deal_payout_txn(deal_uid)
            return await self.get_deal(deal_uid)
        else:
            deal.status = status
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(deal)
            await self.refresh_deal_payout_txn(deal_uid)
            return await self.get_deal(deal_uid)

    async def set_deposit_txn_hash(self, deal_uid: str, tx_hash: str) -> Optional[Deal]:
        """Сохранить хеш транзакции депозита. Вызывать только при status=wait_deposit и только отправителем."""
        deal = await self.get_deal(deal_uid)
        if not deal or deal.status != "wait_deposit":
            return None
        deal.deposit_txn_hash = tx_hash
        deal.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(deal)
        return deal

    async def _is_deposit_tx_confirmed(self, deal_uid: str, tx_hash: str, network: str) -> bool:
        """Проверить подтверждение транзакции депозита в сети. Кеш 10 сек."""
        now = time.time()
        if deal_uid in _deposit_check_cache:
            ts, confirmed = _deposit_check_cache[deal_uid]
            if now - ts < DEPOSIT_CHECK_TTL_SEC:
                return confirmed
        from services.tron.api_client import TronAPIClient
        try:
            async with TronAPIClient(network=network) as client:
                info = await client.get_transaction_info(tx_hash)
        except Exception as e:
            logger.warning("deposit tx check failed for deal %s: %s", deal_uid, e)
            _deposit_check_cache[deal_uid] = (now, False)
            return False
        receipt = info.get("receipt") or {}
        # Успех только при явном result == SUCCESS и транзакции в блоке
        result = receipt.get("result")
        block_ok = (info.get("blockNumber") or info.get("block_timestamp") or info.get("blockTimeStamp") or 0) != 0
        confirmed = result == "SUCCESS" and block_ok
        _deposit_check_cache[deal_uid] = (now, confirmed)
        return confirmed

    async def add_payout_signature(
        self,
        deal_uid: str,
        signer_address: str,
        signature: str,
        signature_index: Optional[int] = None,
        unsigned_tx: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Add an offline signature to the deal's payout transaction.
        Caller must be a participant; signer_address must be one of participants or arbiter.
        Если передан unsigned_tx и подписей ещё нет — подменяем им payout_txn.unsigned_tx (продление срока).

        Args:
            deal_uid: Deal UID
            signer_address: TRON address of the signer
            signature: Signature hex string
            signature_index: Optional index of signer in multisig config (for combine_signatures order)
            unsigned_tx: Optional extended transaction (only applied when there are no signatures yet)

        Returns:
            Updated payout_txn dict or None if deal not found / no payout_txn
        """
        deal = await self.get_deal(deal_uid)
        if not deal:
            return None

        payout = deal.payout_txn
        if not payout or not isinstance(payout, dict):
            return None

        if payout.get("owner_addresses"):
            allowed = set(payout["owner_addresses"])
        else:
            allowed = set(payout.get("participants") or [])
            arbiter = payout.get("arbiter")
            if arbiter:
                allowed.add(arbiter)
        if signer_address not in allowed:
            logger.warning("add_payout_signature: signer_address %s not in participants/arbiter for deal %s", signer_address, deal_uid)
            return None

        signatures = list(payout.get("signatures") or [])
        if any(s.get("signer_address") == signer_address for s in signatures):
            return payout

        # Продлённая транзакция: подменяем только если подписей ещё не было
        if unsigned_tx and isinstance(unsigned_tx, dict):
            if len(signatures) > 0:
                raise ValueError(
                    "Нельзя заменить транзакцию: подписи уже есть. Подписывайте текущую транзакцию."
                )
            payout = {
                **payout,
                "unsigned_tx": unsigned_tx,
                "contract_data": unsigned_tx.get("raw_data") or payout.get("contract_data"),
            }

        entry = {"signer_address": signer_address, "signature": signature}
        if signature_index is not None:
            entry["signature_index"] = signature_index
        signatures.append(entry)
        payout = {**payout, "signatures": signatures}
        deal.payout_txn = payout
        deal.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(deal)

        # Если подписант — получатель, отправляем сервисное сообщение в чат
        receiver_user = (
            await self.session.execute(select(WalletUser).where(WalletUser.did == deal.receiver_did))
        ).scalar_one_or_none()
        if receiver_user and (receiver_user.wallet_address or "").strip().lower() == (signer_address or "").strip().lower():
            try:
                nickname = receiver_user.nickname
                service_text = f"{nickname} {deal.receiver_did} сообщил о выполнении условий сделки"
                chat_svc = ChatService(self.session, deal.receiver_did)
                service_message = ChatMessageCreate(
                    uuid=str(uuid.uuid4()),
                    message_type=MessageType.SERVICE,
                    sender_id=deal.receiver_did,
                    receiver_id=deal.sender_did,
                    deal_uid=deal.uid,
                    deal_label=deal.label,
                    text=service_text,
                )
                await chat_svc.add_message(service_message, deal_uid=deal.uid)
                await self.session.commit()
            except Exception as e:
                logger.warning("add_payout_signature: failed to add receiver completion service message for deal %s: %s", deal_uid, e)

        return deal.payout_txn

    def get_payout_signed_tx(self, deal: Deal) -> Optional[Dict[str, Any]]:
        """
        Собрать подписанную транзакцию выплаты для broadcast, если набрано достаточно подписей.
        Если есть owner_addresses (2-of-3): нужны любые required подписей из владельцев, порядок по индексу.
        Иначе (2-of-2): нужны подписи всех participants.
        """
        payout = deal.payout_txn if deal else None
        if not payout or not isinstance(payout, dict):
            return None
        sigs = payout.get("signatures") or []
        unsigned = payout.get("unsigned_tx")
        if not unsigned or not isinstance(unsigned, dict):
            return None
        by_addr = {str(s.get("signer_address") or "").strip().lower(): (s.get("signature") or "").strip() for s in sigs}

        def norm(hex_sig: str) -> str:
            s = (hex_sig or "").strip()
            return s[2:] if s.startswith("0x") else s

        owners = payout.get("owner_addresses")
        required = payout.get("required_signatures") or 2
        if owners:
            # Мультиподпись N-of-M: любые required подписей из owner_addresses, порядок по индексу
            indexed = []
            for i, addr in enumerate(owners):
                key = str(addr or "").strip().lower()
                hex_sig = by_addr.get(key)
                if hex_sig:
                    indexed.append((i, norm(hex_sig)))
            if len(indexed) < required:
                return None
            indexed.sort(key=lambda x: x[0])
            ordered = [sig for _, sig in indexed][:required]
        else:
            # Нет owner_addresses: кворум по конфигу — required из (participants + arbiter) или все participants
            participants = payout.get("participants") or []
            arbiter = payout.get("arbiter")
            if arbiter:
                owners = list(participants) + [arbiter]
                required = payout.get("required_signatures") or 2
                indexed = []
                for i, addr in enumerate(owners):
                    key = str(addr or "").strip().lower()
                    hex_sig = by_addr.get(key)
                    if hex_sig:
                        indexed.append((i, norm(hex_sig)))
                if len(indexed) < required:
                    return None
                indexed.sort(key=lambda x: x[0])
                ordered = [sig for _, sig in indexed][:required]
            else:
                required = required if payout.get("required_signatures") is not None else len(participants)
                if len(sigs) < required:
                    return None
                ordered = []
                for addr in participants:
                    key = str(addr or "").strip().lower()
                    hex_sig = by_addr.get(key)
                    if not hex_sig:
                        return None
                    ordered.append(norm(hex_sig))
        return {
            **unsigned,
            "signature": ordered,
        }

    async def _is_payout_tx_success(self, tx_hash: str, network: str) -> bool:
        """
        Проверить, что транзакция выплаты в сети имеет статус success (подтверждена).
        При PENDING — повторные запросы до PAYOUT_TX_PENDING_TIMEOUT_SEC (например 10 сек).
        При result != SUCCESS (после ожидания) выбрасывает ValueError с текстом ошибки из сети.
        """
        from services.tron.api_client import TronAPIClient

        PAYOUT_TX_PENDING_TIMEOUT_SEC = 10
        PAYOUT_TX_CHECK_INTERVAL_SEC = 2.5
        max_attempts = max(1, int(PAYOUT_TX_PENDING_TIMEOUT_SEC / PAYOUT_TX_CHECK_INTERVAL_SEC) + 1)

        last_error = None
        for attempt in range(max_attempts):
            if attempt > 0:
                await asyncio.sleep(PAYOUT_TX_CHECK_INTERVAL_SEC)
            try:
                async with TronAPIClient(network=network) as client:
                    info = await client.get_transaction_info(tx_hash)
            except Exception as e:
                logger.warning("payout tx check failed for %s (attempt %s): %s", tx_hash, attempt + 1, e)
                last_error = e
                continue
            receipt = info.get("receipt") or {}
            result = receipt.get("result")
            block_ok = (info.get("blockNumber") or info.get("block_timestamp") or info.get("blockTimeStamp") or 0) != 0
            if result == "SUCCESS":
                return block_ok
            if result == "FAILED" or (result is not None and str(result).upper() not in ("PENDING", "SUCCESS", "")):
                error_msg = receipt.get("result_message") or "Transaction failed"
                contract_result = receipt.get("contractResult") or []
                if contract_result and isinstance(contract_result, list) and len(contract_result) > 0:
                    try:
                        error_msg = contract_result[0].decode("utf-8", errors="replace") if isinstance(contract_result[0], bytes) else str(contract_result[0])
                    except Exception:
                        error_msg = receipt.get("result_message") or str(contract_result[:1])
                raise ValueError(error_msg)
            # PENDING или пустой result — ждём и повторяем
        if last_error:
            logger.warning("payout tx check failed for %s after %s attempts: %s", tx_hash, max_attempts, last_error)
            return False
        raise ValueError("Transaction still pending or not found")

    async def sender_confirm_complete(self, deal_uid: str, payout_tx_hash: Optional[str] = None) -> Optional[Deal]:
        """
        Подтверждение после успешного broadcast выплаты. resolved_sender/resolved_receiver выставляются
        только после проверки финализации tx в сети (_is_payout_tx_success).
        processing + sender -> success; resolving_sender + sender -> resolved_sender; resolving_receiver + receiver -> resolved_receiver.
        """
        deal = await self.get_deal(deal_uid)
        if not deal:
            return None
        if deal.need_receiver_approve:
            return None
        tx_hash = (payout_tx_hash or "").strip() or None
        if deal.status == "processing":
            if self.owner_did != deal.sender_did:
                return None
            if tx_hash and deal.escrow_id:
                result = await self.session.execute(
                    select(EscrowModel).where(EscrowModel.id == deal.escrow_id)
                )
                escrow = result.scalar_one_or_none()
                if escrow and escrow.blockchain == "tron":
                    if not await self._is_payout_tx_success(tx_hash, escrow.network):
                        logger.warning("sender_confirm_complete: payout tx %s not confirmed for deal %s", tx_hash, deal_uid)
                        return None
            try:
                sender_user = (
                    await self.session.execute(select(WalletUser).where(WalletUser.did == deal.sender_did))
                ).scalar_one_or_none()
                nickname = sender_user.nickname if sender_user else deal.sender_did
                service_text = f"{nickname} {deal.sender_did} подтвердил и претензий не имеет"
                chat_svc = ChatService(self.session, deal.sender_did)
                service_message = ChatMessageCreate(
                    uuid=str(uuid.uuid4()),
                    message_type=MessageType.SERVICE,
                    sender_id=deal.sender_did,
                    receiver_id=deal.receiver_did,
                    deal_uid=deal.uid,
                    deal_label=deal.label,
                    text=service_text,
                    txn_hash=tx_hash,
                )
                await chat_svc.add_message(service_message, deal_uid=deal.uid)
            except Exception as e:
                logger.warning("sender_confirm_complete: failed to add service message for deal %s: %s", deal_uid, e)
            deal.status = "success"
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(deal)
            return await self.get_deal(deal_uid)
        if deal.status == "resolving_sender":
            if self.owner_did != deal.sender_did:
                return None
            if not tx_hash or not deal.escrow_id:
                return None
            result = await self.session.execute(
                select(EscrowModel).where(EscrowModel.id == deal.escrow_id)
            )
            escrow = result.scalar_one_or_none()
            if not escrow or escrow.blockchain != "tron":
                return None
            if not await self._is_payout_tx_success(tx_hash, escrow.network):
                logger.warning("sender_confirm_complete: payout tx %s not confirmed for deal %s", tx_hash, deal_uid)
                return None
            try:
                sender_user = (
                    await self.session.execute(select(WalletUser).where(WalletUser.did == deal.sender_did))
                ).scalar_one_or_none()
                nickname = sender_user.nickname if sender_user else deal.sender_did
                service_text = f"{nickname} {deal.sender_did} подтвердил и претензий не имеет"
                chat_svc = ChatService(self.session, deal.sender_did)
                service_message = ChatMessageCreate(
                    uuid=str(uuid.uuid4()),
                    message_type=MessageType.SERVICE,
                    sender_id=deal.sender_did,
                    receiver_id=deal.receiver_did,
                    deal_uid=deal.uid,
                    deal_label=deal.label,
                    text=service_text,
                    txn_hash=tx_hash,
                )
                await chat_svc.add_message(service_message, deal_uid=deal.uid)
            except Exception as e:
                logger.warning("sender_confirm_complete: failed to add service message for deal %s: %s", deal_uid, e)
            deal.status = "resolved_sender"
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(deal)
            return await self.get_deal(deal_uid)
        if deal.status == "resolving_receiver":
            if self.owner_did != deal.receiver_did:
                return None
            if not tx_hash or not deal.escrow_id:
                return None
            result = await self.session.execute(
                select(EscrowModel).where(EscrowModel.id == deal.escrow_id)
            )
            escrow = result.scalar_one_or_none()
            if not escrow or escrow.blockchain != "tron":
                return None
            if not await self._is_payout_tx_success(tx_hash, escrow.network):
                logger.warning("sender_confirm_complete: payout tx %s not confirmed for deal %s", tx_hash, deal_uid)
                return None
            try:
                receiver_user = (
                    await self.session.execute(select(WalletUser).where(WalletUser.did == deal.receiver_did))
                ).scalar_one_or_none()
                nickname = receiver_user.nickname if receiver_user else deal.receiver_did
                service_text = f"{nickname} {deal.receiver_did} подтвердил получение"
                chat_svc = ChatService(self.session, deal.receiver_did)
                service_message = ChatMessageCreate(
                    uuid=str(uuid.uuid4()),
                    message_type=MessageType.SERVICE,
                    sender_id=deal.receiver_did,
                    receiver_id=deal.sender_did,
                    deal_uid=deal.uid,
                    deal_label=deal.label,
                    text=service_text,
                    txn_hash=tx_hash,
                )
                await chat_svc.add_message(service_message, deal_uid=deal.uid)
            except Exception as e:
                logger.warning("sender_confirm_complete: failed to add service message for deal %s: %s", deal_uid, e)
            deal.status = "resolved_receiver"
            deal.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(deal)
            return await self.get_deal(deal_uid)
        return None

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

