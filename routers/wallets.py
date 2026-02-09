"""
Router for Wallet management API
"""
import logging
from fastapi import APIRouter, HTTPException, status
from dependencies import RequireAdminDepends, DbDepends, SettingsDepends
from sqlalchemy import select
from db.models import Wallet, WalletUser
from typing import Dict, List

logger = logging.getLogger(__name__)
from schemas.wallet import (
    CreateWalletRequest,
    UpdateWalletNameRequest,
    WalletResponse,
    WalletListResponse
)
from schemas.node import ChangeResponse
from services.wallet import WalletService
from services.tron.api_client import TronAPIClient

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
            account_permissions=wallet.account_permissions,
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
                account_permissions=wallet.account_permissions,
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
            account_permissions=wallet.account_permissions,
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
            account_permissions=wallet.account_permissions,
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


@router.post("/{wallet_id}/fetch-permissions", response_model=WalletResponse)
async def fetch_wallet_permissions(
    wallet_id: int,
    db: DbDepends,
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Fetch account permissions from TRON blockchain and update wallet
    
    Args:
        wallet_id: Wallet ID
        db: Database session
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        Updated wallet information with account permissions
    """
    try:
        # Get wallet
        result = await db.execute(
            select(Wallet).where(Wallet.id == wallet_id)
        )
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Fetch account info from TRON blockchain
        network = settings.tron.network
        api_key = settings.tron.api_key
        
        async with TronAPIClient(network=network, api_key=api_key) as api:
            account_info = await api.get_account(wallet.tron_address)
            
            if not account_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Account {wallet.tron_address} not found in TRON blockchain"
                )
            
            # Extract permissions
            permissions_data = {
                "owner": account_info.get("owner_permission"),
                "active": account_info.get("active_permission", []),
                "witness": account_info.get("witness_permission")
            }
            
            # Update wallet with permissions
            wallet.account_permissions = permissions_data
            await db.commit()
            await db.refresh(wallet)
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            account_permissions=wallet.account_permissions,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error fetching wallet permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching wallet permissions: {str(e)}"
        )


@router.get("/addresses/{address}/username")
async def get_username_by_address(
    address: str,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get username by wallet address
    
    Args:
        address: Wallet address (TRON or Ethereum)
        db: Database session
        admin: Admin authentication
        
    Returns:
        Username if found, None otherwise
    """
    try:
        result = await db.execute(
            select(WalletUser).where(WalletUser.wallet_address == address)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return {"username": user.nickname, "found": True}
        else:
            return {"username": None, "found": False}
    except Exception as e:
        logger.error(f"Error getting username by address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting username: {str(e)}"
        )

