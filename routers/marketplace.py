"""
Router for Marketplace API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from dependencies import DbDepends, SettingsDepends, require_admin
from services.arbiter import ArbiterService
from schemas.arbiter import (
    CreateArbiterAddressRequest,
    UpdateArbiterAddressNameRequest,
    ArbiterAddressResponse,
    ArbiterAddressListResponse
)

router = APIRouter(
    prefix="/api/marketplace",
    tags=["marketplace"],
    dependencies=[Depends(require_admin)]
)


@router.get("/arbiter/is-initialized")
async def check_arbiter_initialized(
    db: DbDepends
):
    """
    Check if arbiter wallet has been initialized
    
    Args:
        db: Database session
        
    Returns:
        Arbiter initialization status
    """
    is_initialized = await ArbiterService.is_arbiter_initialized(db)
    
    return {"initialized": is_initialized}


@router.post("/arbiter/addresses", response_model=ArbiterAddressResponse, status_code=status.HTTP_201_CREATED)
async def create_arbiter_address(
    request: CreateArbiterAddressRequest,
    db: DbDepends,
    settings: SettingsDepends
):
    """
    Create a new arbiter address from mnemonic phrase
    
    Args:
        request: Arbiter address creation request (name, mnemonic)
        db: Database session
        settings: Application settings
        
    Returns:
        Created arbiter address information
    """
    try:
        wallet = await ArbiterService.create_arbiter_address(
            name=request.name,
            mnemonic=request.mnemonic,
            db=db,
            secret=settings.secret.get_secret_value()
        )
        
        return ArbiterAddressResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            role=wallet.role,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except IntegrityError as e:
        # Обработка ошибок уникальности из БД
        error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
        if 'tron_address' in error_str.lower():
            detail = "TRON адрес уже существует в базе данных"
        elif 'ethereum_address' in error_str.lower():
            detail = "Ethereum адрес уже существует в базе данных"
        else:
            detail = "Адрес уже существует в базе данных"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания кошелька арбитра: {str(e)}"
        )


@router.get("/arbiter/addresses", response_model=ArbiterAddressListResponse)
async def list_arbiter_addresses(
    db: DbDepends
):
    """
    Get list of all arbiter addresses
    
    Args:
        db: Database session
        
    Returns:
        List of arbiter addresses
    """
    try:
        wallets = await ArbiterService.get_arbiter_wallets(db)
        
        address_responses = [
            ArbiterAddressResponse(
                id=wallet.id,
                name=wallet.name,
                tron_address=wallet.tron_address,
                ethereum_address=wallet.ethereum_address,
                role=wallet.role,
                created_at=wallet.created_at,
                updated_at=wallet.updated_at
            )
            for wallet in wallets
        ]
        
        return ArbiterAddressListResponse(
            addresses=address_responses,
            total=len(address_responses)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading arbiter addresses: {str(e)}"
        )


@router.get("/arbiter/addresses/{wallet_id}", response_model=ArbiterAddressResponse)
async def get_arbiter_address(
    wallet_id: int,
    db: DbDepends
):
    """
    Get arbiter address by ID
    
    Args:
        wallet_id: Arbiter address ID
        db: Database session
        
    Returns:
        Arbiter address information
    """
    try:
        wallet = await ArbiterService.get_arbiter_wallet_by_id(wallet_id, db)
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arbiter address not found"
            )
        
        return ArbiterAddressResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            role=wallet.role,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading arbiter address: {str(e)}"
        )


@router.put("/arbiter/addresses/{wallet_id}/name", response_model=ArbiterAddressResponse)
async def update_arbiter_address_name(
    wallet_id: int,
    request: UpdateArbiterAddressNameRequest,
    db: DbDepends
):
    """
    Update arbiter address name
    
    Args:
        wallet_id: Arbiter address ID
        request: Update request with new name
        db: Database session
        
    Returns:
        Updated arbiter address information
    """
    try:
        wallet = await ArbiterService.update_arbiter_address_name(
            wallet_id=wallet_id,
            name=request.name,
            db=db
        )
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arbiter address not found"
            )
        
        return ArbiterAddressResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            role=wallet.role,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating arbiter address name: {str(e)}"
        )


@router.post("/arbiter/addresses/{wallet_id}/activate", response_model=ArbiterAddressResponse)
async def activate_arbiter_address(
    wallet_id: int,
    db: DbDepends
):
    """
    Switch active arbiter address
    
    Makes the specified backup arbiter address active and demotes the current
    active address to backup status.
    
    Args:
        wallet_id: Arbiter address ID to activate (must be 'arbiter-backup')
        db: Database session
        
    Returns:
        Activated arbiter address information
    """
    try:
        wallet = await ArbiterService.switch_active_arbiter_address(wallet_id, db)
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arbiter address not found or cannot be activated"
            )
        
        return ArbiterAddressResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            role=wallet.role,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating arbiter address: {str(e)}"
        )


@router.delete("/arbiter/addresses/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_arbiter_address(
    wallet_id: int,
    db: DbDepends
):
    """
    Delete arbiter address
    
    Args:
        wallet_id: Arbiter address ID
        db: Database session
        
    Returns:
        No content on success
    """
    try:
        deleted = await ArbiterService.delete_arbiter_address(wallet_id, db)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arbiter address not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting arbiter address: {str(e)}"
        )

