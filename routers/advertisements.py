"""
Router for Advertisement management API
"""
from fastapi import APIRouter, HTTPException, Depends
from dependencies import DbDepends, RequireAdminDepends
from routers.auth import get_current_tron_user, UserInfo
from schemas.advertisements import (
    CreateAdvertisementRequest,
    UpdateAdvertisementRequest,
    AdvertisementResponse,
    AdvertisementListResponse,
    AdvertisementSearchRequest
)
from services.advertisement import AdvertisementService
from services.wallet_user import WalletUserService
from ledgers import get_user_did
from db.models import WalletUser
from sqlalchemy import select


async def _advertisement_to_response(advertisement, db):
    """Convert Advertisement model to AdvertisementResponse with user info"""
    # Get user info
    result = await db.execute(
        select(WalletUser).where(WalletUser.id == advertisement.user_id)
    )
    user = result.scalar_one_or_none()
    user_is_verified = user.is_verified if user else False
    owner_nickname = user.nickname if user else None
    owner_avatar = user.avatar if user else None
    owner_did = get_user_did(user.wallet_address, user.blockchain) if user else None
    owner_wallet_address = user.wallet_address if user else None
    owner_blockchain = user.blockchain if user else None
    
    # Create response dict
    ad_dict = {
        "id": advertisement.id,
        "user_id": advertisement.user_id,
        "name": advertisement.name,
        "description": advertisement.description,
        "fee": advertisement.fee,
        "min_limit": advertisement.min_limit,
        "max_limit": advertisement.max_limit,
        "currency": advertisement.currency,
        "is_active": advertisement.is_active,
        "is_verified": advertisement.is_verified,
        "escrow_enabled": advertisement.escrow_enabled,
        "user_is_verified": user_is_verified,
        "rating": advertisement.rating,
        "deals_count": advertisement.deals_count,
        "owner_nickname": owner_nickname,
        "owner_avatar": owner_avatar,
        "owner_did": owner_did,
        "owner_wallet_address": owner_wallet_address,
        "owner_blockchain": owner_blockchain,
        "created_at": advertisement.created_at,
        "updated_at": advertisement.updated_at,
    }
    return AdvertisementResponse(**ad_dict)


# Public router for marketplace
marketplace_router = APIRouter(
    prefix="/api/marketplace",
    tags=["marketplace"]
)

# Private router for user's own advertisements
my_ads_router = APIRouter(
    prefix="/api/my-ads",
    tags=["my-advertisements"]
)


@marketplace_router.post("/search", response_model=AdvertisementListResponse)
async def search_advertisements(
    search_request: AdvertisementSearchRequest,
    db: DbDepends = None
):
    """
    Search advertisements in marketplace with filters
    
    Args:
        search_request: Search parameters
        db: Database session
        
    Returns:
        List of advertisements with pagination info
    """
    try:
        advertisements, total = await AdvertisementService.search_advertisements(
            query=search_request.query,
            currency=search_request.currency,
            is_active=search_request.is_active if search_request.is_active is not None else True,
            is_verified=search_request.is_verified,
            min_amount=search_request.min_amount,
            max_amount=search_request.max_amount,
            page=search_request.page,
            page_size=search_request.page_size,
            db=db
        )
        
        # Convert to response with user info
        ad_responses = []
        for ad in advertisements:
            ad_response = await _advertisement_to_response(ad, db)
            ad_responses.append(ad_response)
        
        return AdvertisementListResponse(
            advertisements=ad_responses,
            total=total,
            page=search_request.page,
            page_size=search_request.page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching advertisements: {str(e)}"
        )


@marketplace_router.get("/{advertisement_id}", response_model=AdvertisementResponse)
async def get_advertisement(
    advertisement_id: int,
    db: DbDepends = None
):
    """
    Get single advertisement by ID
    
    Args:
        advertisement_id: Advertisement ID
        db: Database session
        
    Returns:
        Advertisement details
    """
    try:
        advertisement = await AdvertisementService.get_by_id(advertisement_id, db)
        
        if not advertisement:
            raise HTTPException(
                status_code=404,
                detail="Advertisement not found"
            )
        
        return await _advertisement_to_response(advertisement, db)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching advertisement: {str(e)}"
        )


@my_ads_router.get("", response_model=AdvertisementListResponse)
async def get_my_advertisements(
    page: int = 1,
    page_size: int = 20,
    db: DbDepends = None,
    current_user: UserInfo = Depends(get_current_tron_user)
):
    """
    Get current user's advertisements
    
    Args:
        page: Page number
        page_size: Items per page
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of user's advertisements with pagination
    """
    try:
        # Get user from database
        wallet_address = current_user.wallet_address
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Get user's advertisements
        advertisements, total = await AdvertisementService.get_user_advertisements(
            user_id=user.id,
            page=page,
            page_size=page_size,
            db=db
        )
        
        # Convert to response with user info
        ad_responses = []
        for ad in advertisements:
            ad_response = await _advertisement_to_response(ad, db)
            ad_responses.append(ad_response)
        
        return AdvertisementListResponse(
            advertisements=ad_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching advertisements: {str(e)}"
        )


@my_ads_router.post("", response_model=AdvertisementResponse)
async def create_advertisement(
    request: CreateAdvertisementRequest,
    db: DbDepends = None,
    current_user: UserInfo = Depends(get_current_tron_user)
):
    """
    Create new advertisement
    
    Args:
        request: Advertisement data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created advertisement
    """
    try:
        # Get user from database
        wallet_address = current_user.wallet_address
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Create advertisement
        advertisement = await AdvertisementService.create_advertisement(
            user_id=user.id,
            name=request.name,
            description=request.description,
            fee=request.fee,
            min_limit=request.min_limit,
            max_limit=request.max_limit,
            currency=request.currency,
            db=db
        )
        
        return await _advertisement_to_response(advertisement, db)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating advertisement: {str(e)}"
        )


@my_ads_router.put("/{advertisement_id}", response_model=AdvertisementResponse)
async def update_advertisement(
    advertisement_id: int,
    request: UpdateAdvertisementRequest,
    db: DbDepends = None,
    current_user: UserInfo = Depends(get_current_tron_user)
):
    """
    Update advertisement
    
    Args:
        advertisement_id: Advertisement ID
        request: Updated advertisement data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated advertisement
    """
    try:
        # Get user from database
        wallet_address = current_user.wallet_address
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Update advertisement
        advertisement = await AdvertisementService.update_advertisement(
            advertisement_id=advertisement_id,
            user_id=user.id,
            name=request.name,
            description=request.description,
            fee=request.fee,
            min_limit=request.min_limit,
            max_limit=request.max_limit,
            currency=request.currency,
            is_active=request.is_active,
            escrow_enabled=request.escrow_enabled,
            db=db
        )
        
        return await _advertisement_to_response(advertisement, db)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating advertisement: {str(e)}"
        )


@my_ads_router.delete("/{advertisement_id}")
async def delete_advertisement(
    advertisement_id: int,
    db: DbDepends = None,
    current_user: UserInfo = Depends(get_current_tron_user)
):
    """
    Delete advertisement
    
    Args:
        advertisement_id: Advertisement ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        # Get user from database
        wallet_address = current_user.wallet_address
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Delete advertisement
        await AdvertisementService.delete_advertisement(
            advertisement_id=advertisement_id,
            user_id=user.id,
            db=db
        )
        
        return {"message": "Advertisement deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting advertisement: {str(e)}"
        )


@my_ads_router.post("/{advertisement_id}/toggle-active", response_model=AdvertisementResponse)
async def toggle_advertisement_active(
    advertisement_id: int,
    db: DbDepends = None,
    current_user: UserInfo = Depends(get_current_tron_user)
):
    """
    Toggle advertisement active status
    
    Args:
        advertisement_id: Advertisement ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated advertisement
    """
    try:
        # Get user from database
        wallet_address = current_user.wallet_address
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Toggle status
        advertisement = await AdvertisementService.toggle_active_status(
            advertisement_id=advertisement_id,
            user_id=user.id,
            db=db
        )
        
        return await _advertisement_to_response(advertisement, db)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error toggling advertisement status: {str(e)}"
        )


# Admin router for managing advertisements
admin_ads_router = APIRouter(
    prefix="/api/admin/advertisements",
    tags=["admin-advertisements"]
)


@admin_ads_router.put("/{advertisement_id}/escrow-enabled", response_model=AdvertisementResponse)
async def set_advertisement_escrow_enabled(
    advertisement_id: int,
    escrow_enabled: bool,
    db: DbDepends = None,
    admin: RequireAdminDepends = None
):
    """
    Set escrow_enabled flag for advertisement (admin only)
    
    Args:
        advertisement_id: Advertisement ID
        escrow_enabled: Whether escrow deals are enabled
        db: Database session
        admin: Admin authentication
        
    Returns:
        Updated advertisement
    """
    try:
        # Get advertisement
        advertisement = await AdvertisementService.get_by_id(advertisement_id, db)
        
        if not advertisement:
            raise HTTPException(
                status_code=404,
                detail="Advertisement not found"
            )
        
        # Update escrow_enabled flag (admin can update any advertisement)
        advertisement = await AdvertisementService.update_advertisement(
            advertisement_id=advertisement_id,
            user_id=advertisement.user_id,  # Keep original owner
            escrow_enabled=escrow_enabled,
            db=db
        )
        
        return await _advertisement_to_response(advertisement, db)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating advertisement escrow flag: {str(e)}"
        )

