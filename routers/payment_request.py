"""
Router for Payment Request API
"""
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from routers.auth import get_current_tron_user, UserInfo
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dependencies import DbDepends, SettingsDepends
from services.deals.service import DealsService
from services.wallet_user import WalletUserService
from services.arbiter.service import ArbiterService
from services.escrow.service import EscrowService
from services.chat.service import ChatService
from ledgers import get_user_did
from ledgers.chat.schemas import ChatMessageCreate, MessageType
from routers.utils import get_wallet_address_by_did
from sqlalchemy import select, and_, or_
from db.models import EscrowModel, WalletUser


router = APIRouter(
    prefix="/api/payment-request",
    tags=["payment-request"]
)

# Security для опциональной авторизации
security_optional = HTTPBearer(auto_error=False)


class CreatePaymentRequestRequest(BaseModel):
    """Request для создания заявки на оплату"""
    payer_address: str = Field(..., description="Tron адрес плательщика (того, кто должен оплатить)")
    label: str = Field(..., description="Заголовок заявки на оплату")
    amount: float = Field(..., gt=0, description="Сумма сделки")
    description: Optional[str] = Field(None, description="Описание заявки на оплату (опционально)")
    blockchain: str = Field(default="tron", description="Blockchain name (tron, eth, etc.)")


class PaymentRequestResponse(BaseModel):
    """Response для заявки на оплату"""
    deal_uid: str = Field(..., description="UID сделки")
    sender_did: str = Field(..., description="DID отправителя")
    receiver_did: str = Field(..., description="DID получателя")
    arbiter_did: str = Field(..., description="DID арбитра")
    label: str = Field(..., description="Заголовок")
    description: Optional[str] = Field(None, description="Описание сделки")
    need_receiver_approve: bool = Field(..., description="Требуется ли одобрение получателя")
    status: str = Field(..., description="Статус сделки: processing, success, appeal, resolved_sender, resolved_receiver")
    created_at: str = Field(..., description="Дата создания")
    escrow_address: Optional[str] = Field(None, description="Escrow address")
    escrow_status: Optional[str] = Field(None, description="Escrow status (pending, active, inactive)")
    escrow_id: Optional[int] = Field(None, description="Escrow ID")
    payout_txn: Optional[dict] = Field(None, description="Оффлайн-транзакция выплаты по сделке")


class PayoutSignatureRequest(BaseModel):
    """Request для добавления оффлайн-подписи к выплате по сделке"""
    signer_address: str = Field(..., description="TRON-адрес подписавшего")
    signature: str = Field(..., description="Подпись в hex")
    signature_index: Optional[int] = Field(None, description="Индекс подписанта в multisig (опционально)")
    unsigned_tx: Optional[dict] = Field(None, description="Продлённая транзакция (только при первой подписи, иначе игнорируется)")


class DealStatusUpdateRequest(BaseModel):
    """Request для смены статуса сделки"""
    status: str = Field(..., description="Статус: success, appeal, resolving_sender, resolving_receiver, recline_appeal, processing")


class DepositTxnRequest(BaseModel):
    """Request для сохранения хеша транзакции депозита в эскроу"""
    tx_hash: str = Field(..., description="Хеш транзакции депозита (txID)")


class SenderConfirmCompleteRequest(BaseModel):
    """Request для подтверждения отправителем после broadcast выплаты"""
    tx_hash: Optional[str] = Field(None, description="Хеш транзакции выплаты (txID) для сервисного сообщения")


class RefreshPayoutTxnRequest(BaseModel):
    """Request для пересборки транзакции выплаты (после Failed / Out of Energy)"""
    failed_tx_hash: Optional[str] = Field(None, description="Хеш неудавшейся транзакции для сервисного сообщения")
    reason: Optional[str] = Field(None, description="Причина (например Out of Energy)")


class ReceiverApproveRequest(BaseModel):
    """Request для одобрения получателем"""
    deal_uid: str = Field(..., description="UID сделки для одобрения")


class ReceiverApproveResponse(BaseModel):
    """Response для одобрения получателем"""
    deal_uid: str = Field(..., description="UID сделки")
    approved: bool = Field(..., description="Статус одобрения")
    message: str = Field(..., description="Сообщение о результате")


async def get_deals_service(
    current_user: UserInfo = Depends(get_current_tron_user),
    db: DbDepends = None
) -> DealsService:
    """
    Dependency для создания DealsService с owner_did текущего пользователя
    
    Args:
        current_user: Текущий авторизованный пользователь
        db: Database session
        
    Returns:
        DealsService instance с настроенным owner_did
    """
    # Получаем пользователя из БД для получения blockchain и DID
    user = await WalletUserService.get_by_wallet_address(current_user.wallet_address, db)
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )
    
    # Получаем DID пользователя
    user_did = get_user_did(user.wallet_address, user.blockchain)
    
    if not user_did:
        raise HTTPException(
            status_code=400,
            detail="User DID not found"
        )
    
    # Создаем DealsService с owner_did (receiver)
    return DealsService(session=db, owner_did=user_did)


@router.post("/create", response_model=PaymentRequestResponse)
async def create_payment_request(
    request: CreatePaymentRequestRequest,
    deals_service: DealsService = Depends(get_deals_service),
    db: DbDepends = None,
    settings: SettingsDepends = None
):
    """
    Создать заявку на оплату
    
    Текущий пользователь (receiver) создает заявку на оплату для sender.
    При создании need_receiver_approve устанавливается в true.
    Арбитр выбирается автоматически из активных арбитров.
    
    Args:
        request: Данные заявки на оплату
        deals_service: DealsService instance (автоматически создается с owner_did текущего пользователя как receiver)
        db: Database session
        
    Returns:
        Созданная заявка на оплату
    """
    try:
        # Получаем активного арбитра
        active_arbiter = await ArbiterService.get_active_arbiter_wallet(db)
        if not active_arbiter:
            raise HTTPException(
                status_code=400,
                detail="Active arbiter not found. Please configure an arbiter first."
            )
        
        # Получаем DID арбитра по его адресу
        arbiter_did = get_user_did(active_arbiter.tron_address, 'tron')
        
        # Получаем DID плательщика по адресу
        payer_did = get_user_did(request.payer_address, 'tron')
        
        # Создаем Escrow через EscrowService перед созданием сделки
        escrow_address = None
        escrow_status = None
        escrow_id = None
        try:
            # Получаем адреса кошельков по DID из БД
            # Для арбитра используем адрес напрямую из active_arbiter
            arbiter_address = active_arbiter.tron_address
            sender_address = await get_wallet_address_by_did(payer_did, db)
            receiver_address = await get_wallet_address_by_did(deals_service.owner_did, db)
            
            # Получаем secret из settings
            secret = settings.secret.get_secret_value()
            
            # Создаем EscrowService
            escrow_service = EscrowService(
                session=db,
                owner_did=deals_service.owner_did,
                secret=secret,
                escrow_type="multisig",
                blockchain=request.blockchain,
                network="mainnet"
            )
            
            # Создаем или получаем существующий escrow
            escrow = await escrow_service.ensure_exists(
                arbiter_address=arbiter_address,
                sender_address=sender_address,
                receiver_address=receiver_address
            )
            
            escrow_address = escrow.escrow_address
            escrow_status = escrow.status
            escrow_id = escrow.id
            
            # Flush чтобы получить escrow.id, commit будет сделан в create_deal
            await db.flush()
            
        except HTTPException:
            # Пробрасываем HTTPException дальше
            raise
        except Exception as e:
            # Логируем ошибку, но не прерываем создание сделки
            print(f"Error creating escrow: {str(e)}")
            # Продолжаем без escrow информации
        
        # Создаем сделку, где текущий пользователь является receiver
        # owner_did (receiver) создает сделку для sender
        # Передаем escrow_id если escrow был создан
        # create_deal сделает commit транзакции
        deal = await deals_service.create_deal(
            sender_did=payer_did,
            receiver_did=deals_service.owner_did,  # Текущий пользователь - receiver
            arbiter_did=arbiter_did,
            label=request.label,
            amount=request.amount,
            description=request.description,
            need_receiver_approve=True,  # Всегда true для заявок на оплату
            escrow_id=escrow_id
        )
        
        return PaymentRequestResponse(
            deal_uid=deal.uid,
            sender_did=deal.sender_did,
            receiver_did=deal.receiver_did,
            arbiter_did=deal.arbiter_did,
            label=deal.label,
            description=deal.description,
            need_receiver_approve=deal.need_receiver_approve,
            status=deal.status,
            created_at=deal.created_at.isoformat(),
            escrow_address=escrow_address,
            escrow_status=escrow_status,
            escrow_id=escrow_id,
            payout_txn=deal.payout_txn,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500,
            detail=f"Error creating payment request: {str(e)}"
        )


@router.post("/receiver-approve", response_model=ReceiverApproveResponse)
async def receiver_approve(
    request: ReceiverApproveRequest,
    deals_service: DealsService = Depends(get_deals_service)
):
    """
    Одобрить заявку на оплату отправителем
    
    Только текущий пользователь, который является sender в сделке, может одобрить заявку.
    Апрув возможен только если need_receiver_approve = true.
    После одобрения need_receiver_approve устанавливается в false.
    
    Args:
        request: Данные для одобрения (deal_uid)
        deals_service: DealsService instance (автоматически создается с owner_did текущего пользователя)
        
    Returns:
        Результат одобрения
    """
    try:
        # Получаем сделку
        deal = await deals_service.get_deal(request.deal_uid)
        
        if not deal:
            raise HTTPException(
                status_code=404,
                detail="Deal not found"
            )
        
        # Проверяем, что заявка требует одобрения
        if not deal.need_receiver_approve:
            return ReceiverApproveResponse(
                deal_uid=deal.uid,
                approved=True,
                message="Payment request already approved or does not require approval"
            )
        
        # Проверяем, что текущий пользователь является sender
        if deal.sender_did != deals_service.owner_did:
            raise HTTPException(
                status_code=403,
                detail="Only sender can approve payment request"
            )
        
        # Обновляем need_receiver_approve на false
        # Используем update_deal, но нам нужно проверить права доступа
        # Поскольку update_deal требует, чтобы owner_did был sender_did, а у нас receiver,
        # нужно обновить напрямую через сессию
        
        deal.need_receiver_approve = False

        # Отправляем в чат сделки сервисное сообщение о подтверждении условий
        approver = await deals_service.session.execute(
            select(WalletUser).where(WalletUser.did == deals_service.owner_did)
        )
        approver_user = approver.scalar_one_or_none()
        nickname = approver_user.nickname if approver_user else deals_service.owner_did
        service_text = f"{nickname} {deals_service.owner_did} принял условия сделки"
        chat_service = ChatService(deals_service.session, deals_service.owner_did)
        service_message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.SERVICE,
            sender_id=deals_service.owner_did,
            receiver_id=deal.receiver_did,
            deal_uid=deal.uid,
            deal_label=deal.label,
            text=service_text,
        )
        await chat_service.add_message(service_message, deal_uid=deal.uid)

        await deals_service.session.commit()
        await deals_service.session.refresh(deal)
        
        return ReceiverApproveResponse(
            deal_uid=deal.uid,
            approved=True,
            message="Payment request approved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error approving payment request: {str(e)}"
        )


@router.get("/list", response_model=dict)
async def list_payment_requests(
    page: int = 1,
    page_size: int = 50,
    deals_service: DealsService = Depends(get_deals_service),
    db: DbDepends = None
):
    """
    Получить список всех сделок, где текущий пользователь является участником
    (sender, receiver или arbiter)
    
    Args:
        page: Номер страницы (начиная с 1)
        page_size: Количество заявок на странице
        deals_service: DealsService instance
        db: Database session
        
    Returns:
        Список всех сделок пользователя с пагинацией
    """
    try:
        result = await deals_service.list_deals(
            page=page,
            page_size=page_size,
            order_by="created_at"
        )
        
        # Преобразуем все сделки в формат для отображения
        payment_requests = []
        for deal in result.get('deals', []):
            # Определяем роль пользователя в сделке
            user_role = None
            if deal.sender_did == deals_service.owner_did:
                user_role = 'sender'
            elif deal.receiver_did == deals_service.owner_did:
                user_role = 'receiver'
            elif deal.arbiter_did == deals_service.owner_did:
                user_role = 'arbiter'
            
            # Получаем информацию об escrow для сделки
            escrow_status = None
            escrow_address = None
            if deal.escrow_id:
                # Если есть escrow_id, получаем escrow напрямую
                escrow_stmt = select(EscrowModel).where(EscrowModel.id == deal.escrow_id)
                escrow_result = await db.execute(escrow_stmt)
                escrow = escrow_result.scalar_one_or_none()
                if escrow:
                    escrow_status = escrow.status
                    escrow_address = escrow.escrow_address
            # Если escrow_id нет, возвращаем пустые значения (escrow_status и escrow_address уже None)
            
            payment_requests.append({
                'deal_uid': deal.uid,
                'sender_did': deal.sender_did,
                'receiver_did': deal.receiver_did,
                'arbiter_did': deal.arbiter_did,
                'label': deal.label,
                'need_receiver_approve': deal.need_receiver_approve,
                'status': deal.status,
                'created_at': deal.created_at.isoformat() if deal.created_at else None,
                'requisites': deal.requisites,
                'user_role': user_role,  # Добавляем роль пользователя
                'escrow_status': escrow_status,  # Статус escrow
                'escrow_address': escrow_address,  # Адрес escrow
                'escrow_id': deal.escrow_id,  # ID escrow
                'payout_txn': deal.payout_txn,
                'payout_txn_hash': deal.payout_txn_hash,
            })
        
        return {
            'payment_requests': payment_requests,
            'total': result.get('total', 0),
            'page': page,
            'page_size': page_size
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing payment requests: {str(e)}"
        )


class GetDidByAddressRequest(BaseModel):
    """Request для получения DID по адресу"""
    wallet_address: str = Field(..., description="Tron адрес кошелька")


class GetDidByAddressResponse(BaseModel):
    """Response для получения DID по адресу"""
    wallet_address: str = Field(..., description="Адрес кошелька")
    did: str = Field(..., description="DID пользователя")
    blockchain: str = Field(..., description="Блокчейн")


@router.post("/get-did-by-address", response_model=GetDidByAddressResponse)
async def get_did_by_address(
    request: GetDidByAddressRequest,
    db: DbDepends = None
):
    """
    Получить DID пользователя по его Tron адресу
    
    Args:
        request: Данные запроса (wallet_address)
        db: Database session
        
    Returns:
        DID пользователя
    """
    try:
        # Получаем пользователя из БД
        user = await WalletUserService.get_by_wallet_address(request.wallet_address, db)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Получаем DID пользователя
        user_did = get_user_did(user.wallet_address, user.blockchain)
        
        if not user_did:
            raise HTTPException(
                status_code=404,
                detail="User DID not found"
            )
        
        return GetDidByAddressResponse(
            wallet_address=user.wallet_address,
            did=user_did,
            blockchain=user.blockchain
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting DID by address: {str(e)}"
        )


class DealInfoResponse(BaseModel):
    """Response для информации о сделке"""
    deal_uid: str = Field(..., description="UID сделки")
    sender_did: str = Field(..., description="DID отправителя")
    receiver_did: str = Field(..., description="DID получателя")
    arbiter_did: str = Field(..., description="DID арбитра")
    sender_address: Optional[str] = Field(None, description="Tron-адрес отправителя")
    receiver_address: Optional[str] = Field(None, description="Tron-адрес получателя")
    label: str = Field(..., description="Заголовок")
    description: Optional[str] = Field(None, description="Описание сделки")
    need_receiver_approve: bool = Field(..., description="Требуется ли одобрение получателя")
    status: str = Field(..., description="Статус сделки: processing, success, appeal, resolved_sender, resolved_receiver")
    created_at: str = Field(..., description="Дата создания")
    updated_at: str = Field(..., description="Дата обновления")
    requisites: Optional[dict] = Field(None, description="Реквизиты сделки")
    attachments: Optional[list] = Field(None, description="Вложения")
    payout_txn: Optional[dict] = Field(None, description="Оффлайн-транзакция выплаты по сделке")
    escrow_status: Optional[str] = Field(None, description="Статус эскроу: pending, active, inactive")
    escrow_address: Optional[str] = Field(None, description="Адрес эскроу-счёта")
    deposit_txn_hash: Optional[str] = Field(None, description="Хеш транзакции депозита в эскроу")
    payout_txn_hash: Optional[str] = Field(None, description="Хеш подтверждённой транзакции выплаты (только при success/resolved_*)")
    amount: Optional[float] = Field(None, description="Сумма сделки (для депозита в эскроу)")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> Optional[UserInfo]:
    """
    Опциональная авторизация - возвращает UserInfo если токен валиден, иначе None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_tron_user(credentials)
    except:
        return None


@router.get("/{deal_uid}", response_model=DealInfoResponse)
async def get_deal_info(
    deal_uid: str,
    db: DbDepends = None,
    user_info: Optional[UserInfo] = Depends(get_optional_user)
):
    """
    Получить информацию о сделке по UID (публичный доступ)
    
    Args:
        deal_uid: UID сделки
        db: Database session
        user_info: Optional user info (если авторизован)
        
    Returns:
        Информация о сделке
    """
    try:
        # Создаем сервис с owner_did, если пользователь авторизован
        if user_info:
            owner_did = get_user_did(user_info.wallet_address, 'tron')
            deals_service = DealsService(owner_did=owner_did, session=db)
            # Пытаемся получить с проверкой участника
            deal = await deals_service.get_deal(deal_uid)
        else:
            # Для неавторизованных используем публичный метод
            deals_service = DealsService(owner_did=None, session=db)
            deal = await deals_service.get_deal_public(deal_uid)
        
        if not deal:
            raise HTTPException(
                status_code=404,
                detail="Deal not found"
            )

        payout_txn = deal.payout_txn
        if user_info:
            try:
                payout_payload = await deals_service.get_or_build_deal_payout_txn(deal_uid)
                if payout_payload is not None:
                    payout_txn = payout_payload
                # Перезагружаем сделку: get_or_build_deal_payout_txn мог перевести wait_deposit -> processing
                deal = await deals_service.get_deal(deal_uid) or deal
            except Exception:
                pass

        escrow_status = None
        escrow_address = None
        if deal.escrow_id:
            escrow_stmt = select(EscrowModel).where(EscrowModel.id == deal.escrow_id)
            escrow_result = await db.execute(escrow_stmt)
            escrow = escrow_result.scalar_one_or_none()
            if escrow:
                escrow_status = escrow.status
                escrow_address = escrow.escrow_address

        sender_address = None
        receiver_address = None
        try:
            sender_address = await get_wallet_address_by_did(deal.sender_did, db)
        except Exception:
            pass
        try:
            receiver_address = await get_wallet_address_by_did(deal.receiver_did, db)
        except Exception:
            pass

        return DealInfoResponse(
            deal_uid=deal.uid,
            sender_did=deal.sender_did,
            receiver_did=deal.receiver_did,
            arbiter_did=deal.arbiter_did,
            sender_address=sender_address,
            receiver_address=receiver_address,
            label=deal.label,
            description=deal.description,
            need_receiver_approve=deal.need_receiver_approve,
            status=deal.status,
            created_at=deal.created_at.isoformat() if deal.created_at else None,
            updated_at=deal.updated_at.isoformat() if deal.updated_at else None,
            requisites=deal.requisites,
            attachments=deal.attachments,
            payout_txn=payout_txn,
            escrow_status=escrow_status,
            escrow_address=escrow_address,
            deposit_txn_hash=deal.deposit_txn_hash,
            payout_txn_hash=deal.payout_txn_hash,
            amount=float(deal.amount) if deal.amount is not None else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting deal info: {str(e)}"
        )


@router.patch("/{deal_uid}/status")
async def update_deal_status(
    deal_uid: str,
    body: DealStatusUpdateRequest,
    deals_service: DealsService = Depends(get_deals_service),
    db: DbDepends = None,
):
    """
    Сменить статус сделки. appeal — sender/receiver из processing или арбитр из финальных;
    resolving_sender/resolving_receiver, recline_appeal, processing — только арбитр.
    resolved_sender/resolved_receiver выставляются только через confirm-complete.
    """
    ALLOWED = {"success", "appeal", "resolving_sender", "resolving_receiver", "recline_appeal", "processing"}
    if body.status not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {ALLOWED}")
    deal = await deals_service.get_deal(deal_uid)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.need_receiver_approve:
        raise HTTPException(status_code=403, detail="Deal not started: receiver approval required")
    owner_did = deals_service.owner_did
    # Из аппеляционных статусов только арбитр может менять
    if deal.status in ("wait_arbiter", "appeal", "recline_appeal", "resolving_sender", "resolving_receiver"):
        if owner_did != deal.arbiter_did:
            raise HTTPException(status_code=403, detail="В состоянии апелляции статус может менять только арбитр")
    # Из финальных статусов только арбитр может менять (в appeal или processing)
    if deal.status in ("success", "resolved_sender", "resolved_receiver"):
        if owner_did != deal.arbiter_did:
            raise HTTPException(status_code=403, detail="Из финального статуса только арбитр может вернуть сделку")
        if body.status not in ("appeal", "processing"):
            raise HTTPException(status_code=403, detail="Из финального статуса разрешены только appeal или processing")
    if body.status == "success":
        if owner_did != deal.receiver_did:
            raise HTTPException(status_code=403, detail="Only receiver can set status to success")
    elif body.status == "appeal":
        if deal.status == "processing":
            if owner_did not in (deal.sender_did, deal.receiver_did):
                raise HTTPException(status_code=403, detail="Only sender or receiver can file appeal")
        elif deal.status in ("success", "resolved_sender", "resolved_receiver"):
            if owner_did != deal.arbiter_did:
                raise HTTPException(status_code=403, detail="Only arbiter can return deal to appeal from final status")
        else:
            raise HTTPException(status_code=403, detail="Appeal only from processing or final status (arbiter)")
    elif body.status in ("resolving_sender", "resolving_receiver"):
        if owner_did != deal.arbiter_did:
            raise HTTPException(status_code=403, detail="Only arbiter can resolve appeal")
        if deal.status not in ("wait_arbiter", "appeal", "recline_appeal"):
            raise HTTPException(status_code=403, detail="Resolving only from wait_arbiter, appeal or recline_appeal")
    elif body.status == "recline_appeal":
        if owner_did != deal.arbiter_did:
            raise HTTPException(status_code=403, detail="Only arbiter can recline appeal")
        if deal.status not in ("resolving_sender", "resolving_receiver"):
            raise HTTPException(status_code=403, detail="Recline only from resolving_sender or resolving_receiver")
    elif body.status == "processing":
        if owner_did != deal.arbiter_did:
            raise HTTPException(status_code=403, detail="Only arbiter can return deal to processing")
    try:
        updated = await deals_service.set_deal_status(deal_uid, body.status)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update status")
    return {
        "deal_uid": updated.uid,
        "status": updated.status,
        "updated_at": updated.updated_at.isoformat() if updated.updated_at else None,
    }


@router.post("/{deal_uid}/payout-signature")
async def add_payout_signature(
    deal_uid: str,
    body: PayoutSignatureRequest,
    deals_service: DealsService = Depends(get_deals_service),
):
    """
    Добавить оффлайн-подпись участника к транзакции выплаты по сделке.
    Вызывающий должен быть участником сделки; signer_address должен быть из participants или arbiter.
    """
    try:
        result = await deals_service.add_payout_signature(
            deal_uid=deal_uid,
            signer_address=body.signer_address,
            signature=body.signature,
            signature_index=body.signature_index,
            unsigned_tx=body.unsigned_tx,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Deal not found, or no payout transaction, or signer not allowed",
        )
    return {"payout_txn": result}


@router.get("/{deal_uid}/payout-signed-tx")
async def get_payout_signed_tx(
    deal_uid: str,
    deals_service: DealsService = Depends(get_deals_service),
):
    """
    Получить собранную подписанную транзакцию выплаты для broadcast (когда набрано достаточно подписей).
    Участник сделки может вызвать для отправки транзакции в сеть с веб-кошелька.
    """
    deal = await deals_service.get_deal(deal_uid)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not deals_service._is_participant(deal):
        raise HTTPException(status_code=403, detail="Not a participant")
    signed_tx = deals_service.get_payout_signed_tx(deal)
    if not signed_tx:
        detail = "Not enough signatures or no payout transaction"
        payout = deal.payout_txn if deal else None
        if payout and isinstance(payout, dict):
            sigs = payout.get("signatures") or []
            by_addr = {str(s.get("signer_address") or "").strip().lower() for s in sigs}
            # Список подписантов: owner_addresses или participants + arbiter (конфиг мультиподписи)
            owners = payout.get("owner_addresses")
            if not owners:
                participants = payout.get("participants") or []
                arbiter = payout.get("arbiter")
                owners = list(participants) + ([arbiter] if arbiter else [])
            required = payout.get("required_signatures") or 2
            missing = [a for a in owners if str(a or "").strip().lower() not in by_addr]
            signed_count = len(owners) - len(missing)
            # Ошибку только если кворум не набран
            if signed_count < required:
                if missing:
                    short = [a[:8] + "…" + a[-4:] if len(a) > 12 else a for a in missing]
                    detail = f"Need {required} of {len(owners)} signatures. Missing: " + ", ".join(short)
                else:
                    detail = f"Need {required} of {len(owners)} signatures."
        raise HTTPException(status_code=400, detail=detail)
    return {"signed_tx": signed_tx}


@router.post("/{deal_uid}/refresh-payout-txn")
async def refresh_payout_txn(
    deal_uid: str,
    body: Optional[RefreshPayoutTxnRequest] = Body(None),
    deals_service: DealsService = Depends(get_deals_service),
):
    """
    Пересборка транзакции выплаты для повторной попытки (например после Failed / Out of Energy).
    Только отправитель, только при status=processing. В чат отправляется сервисное сообщение.
    """
    failed_tx_hash = (body and body.failed_tx_hash and body.failed_tx_hash.strip()) or None
    reason = (body and body.reason and body.reason.strip()) or None
    result = await deals_service.refresh_payout_txn_for_retry(
        deal_uid, failed_tx_hash=failed_tx_hash, reason=reason
    )
    if not result:
        raise HTTPException(
            status_code=403,
            detail="Deal not found, or only sender can refresh, or status is not processing",
        )
    return {"payout_txn": result}


@router.post("/{deal_uid}/sender-confirm-complete")
async def sender_confirm_complete(
    deal_uid: str,
    body: Optional[SenderConfirmCompleteRequest] = Body(None),
    deals_service: DealsService = Depends(get_deals_service),
):
    """
    Подтверждение после broadcast выплаты: processing+sender -> success; resolving_sender+sender -> resolved_sender;
    resolving_receiver+receiver -> resolved_receiver. tx_hash обязателен для resolving_*; проверяется финализация в сети.
    """
    tx_hash = (body and body.tx_hash and body.tx_hash.strip()) or None
    try:
        updated = await deals_service.sender_confirm_complete(deal_uid, payout_tx_hash=tx_hash)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(
            status_code=403,
            detail="Deal not found or only sender can confirm complete",
        )
    return {
        "deal_uid": updated.uid,
        "status": updated.status,
        "updated_at": updated.updated_at.isoformat() if updated.updated_at else None,
    }


@router.post("/{deal_uid}/deposit-txn")
async def set_deposit_txn(
    deal_uid: str,
    body: DepositTxnRequest,
    deals_service: DealsService = Depends(get_deals_service),
):
    """
    Сохранить хеш транзакции депозита в эскроу. Только отправитель, только при статусе wait_deposit.
    """
    deal = await deals_service.get_deal(deal_uid)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status != "wait_deposit":
        raise HTTPException(status_code=400, detail="Deposit tx can be set only when deal status is wait_deposit")
    if deals_service.owner_did != deal.sender_did:
        raise HTTPException(status_code=403, detail="Only sender can set deposit transaction hash")
    updated = await deals_service.set_deposit_txn_hash(deal_uid, body.tx_hash.strip())
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update deposit_txn_hash")
    return {
        "deal_uid": updated.uid,
        "deposit_txn_hash": updated.deposit_txn_hash,
        "status": updated.status,
    }

