"""
Router for Payment Request API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from routers.auth import get_current_tron_user, UserInfo
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dependencies import DbDepends
from services.deals.service import DealsService
from services.wallet_user import WalletUserService
from services.arbiter.service import ArbiterService
from ledgers import get_user_did


router = APIRouter(
    prefix="/api/payment-request",
    tags=["payment-request"]
)

# Security для опциональной авторизации
security_optional = HTTPBearer(auto_error=False)


class CreatePaymentRequestRequest(BaseModel):
    """Request для создания заявки на оплату"""
    payer_address: str = Field(..., description="Tron адрес плательщика (того, кто должен оплатить)")
    label: str = Field(..., description="Заголовок/описание заявки на оплату")


class PaymentRequestResponse(BaseModel):
    """Response для заявки на оплату"""
    deal_uid: str = Field(..., description="UID сделки")
    sender_did: str = Field(..., description="DID отправителя")
    receiver_did: str = Field(..., description="DID получателя")
    arbiter_did: str = Field(..., description="DID арбитра")
    label: str = Field(..., description="Заголовок/описание")
    need_receiver_approve: bool = Field(..., description="Требуется ли одобрение получателя")
    created_at: str = Field(..., description="Дата создания")


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
    db: DbDepends = None
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
        
        # Создаем сделку, где текущий пользователь является receiver
        # owner_did (receiver) создает сделку для sender
        deal = await deals_service.create_deal(
            sender_did=payer_did,
            receiver_did=deals_service.owner_did,  # Текущий пользователь - receiver
            arbiter_did=arbiter_did,
            label=request.label,
            need_receiver_approve=True  # Всегда true для заявок на оплату
        )
        
        return PaymentRequestResponse(
            deal_uid=deal.uid,
            sender_did=deal.sender_did,
            receiver_did=deal.receiver_did,
            arbiter_did=deal.arbiter_did,
            label=deal.label,
            need_receiver_approve=deal.need_receiver_approve,
            created_at=deal.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
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
    deals_service: DealsService = Depends(get_deals_service)
):
    """
    Получить список всех сделок, где текущий пользователь является участником
    (sender, receiver или arbiter)
    
    Args:
        page: Номер страницы (начиная с 1)
        page_size: Количество заявок на странице
        deals_service: DealsService instance
        
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
            
            payment_requests.append({
                'deal_uid': deal.uid,
                'sender_did': deal.sender_did,
                'receiver_did': deal.receiver_did,
                'arbiter_did': deal.arbiter_did,
                'label': deal.label,
                'need_receiver_approve': deal.need_receiver_approve,
                'created_at': deal.created_at.isoformat() if deal.created_at else None,
                'requisites': deal.requisites,
                'user_role': user_role  # Добавляем роль пользователя
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
    label: str = Field(..., description="Заголовок/описание")
    need_receiver_approve: bool = Field(..., description="Требуется ли одобрение получателя")
    created_at: str = Field(..., description="Дата создания")
    updated_at: str = Field(..., description="Дата обновления")
    requisites: Optional[dict] = Field(None, description="Реквизиты сделки")
    attachments: Optional[list] = Field(None, description="Вложения")


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
        
        return DealInfoResponse(
            deal_uid=deal.uid,
            sender_did=deal.sender_did,
            receiver_did=deal.receiver_did,
            arbiter_did=deal.arbiter_did,
            label=deal.label,
            need_receiver_approve=deal.need_receiver_approve,
            created_at=deal.created_at.isoformat() if deal.created_at else None,
            updated_at=deal.updated_at.isoformat() if deal.updated_at else None,
            requisites=deal.requisites,
            attachments=deal.attachments
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting deal info: {str(e)}"
        )

