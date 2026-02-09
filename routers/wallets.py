"""
Router for Wallet management API
"""
import logging
from fastapi import APIRouter, HTTPException, status
from dependencies import RequireAdminDepends, DbDepends, SettingsDepends

logger = logging.getLogger(__name__)
from schemas.wallet import (
    CreateWalletRequest,
    UpdateWalletNameRequest,
    WalletResponse,
    WalletListResponse
)
from schemas.node import ChangeResponse
from services.wallet import WalletService

router = APIRouter(
    prefix="/api/wallets",
    tags=["wallets"]
)


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    request: CreateWalletRequest,
    db: DbDepends,
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Create a new wallet from mnemonic phrase
    
    Args:
        request: Wallet creation request (name, mnemonic)
        db: Database session
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        Created wallet information
    """
    try:
        wallet = await WalletService.create_wallet(
            name=request.name,
            mnemonic=request.mnemonic,
            db=db,
            secret=settings.secret.get_secret_value()
        )
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating wallet: {str(e)}"
        )


@router.get("", response_model=WalletListResponse)
async def list_wallets(
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get list of all wallets
    
    Args:
        db: Database session
        admin: Admin authentication
        
    Returns:
        List of wallets
    """
    try:
        wallets = await WalletService.get_wallets(db)
        
        wallet_responses = [
            WalletResponse(
                id=wallet.id,
                name=wallet.name,
                tron_address=wallet.tron_address,
                ethereum_address=wallet.ethereum_address,
                created_at=wallet.created_at,
                updated_at=wallet.updated_at
            )
            for wallet in wallets
        ]
        
        return WalletListResponse(
            wallets=wallet_responses,
            total=len(wallet_responses)
        )
    except Exception as e:
        import traceback
        error_detail = str(e)
        # Проверяем, не связана ли ошибка с отсутствием таблицы
        if "does not exist" in error_detail.lower() or "relation" in error_detail.lower():
            error_detail = "Таблица wallets не найдена. Выполните миграцию: alembic upgrade head"
        logger.error(f"Error loading wallets: {error_detail}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading wallets: {error_detail}"
        )


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: int,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get wallet by ID
    
    Args:
        wallet_id: Wallet ID
        db: Database session
        admin: Admin authentication
        
    Returns:
        Wallet information
    """
    try:
        wallet = await WalletService.get_wallet(wallet_id, db)
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading wallet: {str(e)}"
        )


@router.put("/{wallet_id}/name", response_model=WalletResponse)
async def update_wallet_name(
    wallet_id: int,
    request: UpdateWalletNameRequest,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Update wallet name
    
    Args:
        wallet_id: Wallet ID
        request: Update request with new name
        db: Database session
        admin: Admin authentication
        
    Returns:
        Updated wallet information
    """
    try:
        wallet = await WalletService.update_wallet_name(
            wallet_id=wallet_id,
            name=request.name,
            db=db
        )
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating wallet: {str(e)}"
        )


@router.delete("/{wallet_id}", response_model=ChangeResponse)
async def delete_wallet(
    wallet_id: int,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Delete wallet
    
    Args:
        wallet_id: Wallet ID
        db: Database session
        admin: Admin authentication
        
    Returns:
        Success status
    """
    try:
        deleted = await WalletService.delete_wallet(wallet_id, db)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return ChangeResponse(
            success=True,
            message="Wallet deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting wallet: {str(e)}"
        )

