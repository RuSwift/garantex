"""
Router for WalletUser management API
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from dependencies import RequireAdminDepends, DbDepends

logger = logging.getLogger(__name__)
from routers.auth import get_current_tron_user, get_current_user
from ledgers import get_user_did
from schemas.node import ChangeResponse
from schemas.users import (
    WalletUserItem, 
    WalletUserList, 
    CreateWalletUserRequest,
    UpdateWalletUserRequest,
    UpdateProfileRequest,
    ProfileResponse
)
from schemas.billing import BillingList, BillingItem
from typing import Dict, Any
from db.models import WalletUser, Billing
from services.wallet_user import WalletUserService
from sqlalchemy import select, func, or_, desc

router = APIRouter(
    prefix="/api/admin/wallet-users",
    tags=["wallet-users"]
)

# Public router for user profile management
profile_router = APIRouter(
    prefix="/api/profile",
    tags=["profile"]
)


@router.get("", response_model=WalletUserList)
async def list_wallet_users(
    page: int = 1,
    page_size: int = 20,
    query: str = None,
    blockchain: str = None,
    access_to_admin_panel: str = Query(None, description="Filter by admin panel access (true/false for managers only)"),
    db: DbDepends = None,
    admin: RequireAdminDepends = None
):
    """
    Get list of wallet users with pagination and search
    
    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page
        query: Search query (wallet address or nickname)
        blockchain: Filter by blockchain type
        access_to_admin_panel: Filter by admin panel access (True for managers only)
        db: Database session
        admin: Admin authentication
        
    Returns:
        List of wallet users with pagination info
    """
    try:
        # Build base query
        stmt = select(WalletUser)
        count_stmt = select(func.count(WalletUser.id))
        
        # Apply filters
        if query:
            search_filter = or_(
                WalletUser.wallet_address.ilike(f"%{query}%"),
                WalletUser.nickname.ilike(f"%{query}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)
        
        if blockchain:
            stmt = stmt.where(WalletUser.blockchain == blockchain)
            count_stmt = count_stmt.where(WalletUser.blockchain == blockchain)
        
        if access_to_admin_panel is not None:
            # Convert string to boolean - handle both string and boolean inputs
            if isinstance(access_to_admin_panel, str):
                filter_value = access_to_admin_panel.lower() in ('true', '1', 'yes', 'on')
            else:
                filter_value = bool(access_to_admin_panel)
            
            logger.info(f"Filtering by access_to_admin_panel: input={access_to_admin_panel} (type={type(access_to_admin_panel)}), filter_value={filter_value}")
            
            # Apply filter
            stmt = stmt.where(WalletUser.access_to_admin_panel == filter_value)
            count_stmt = count_stmt.where(WalletUser.access_to_admin_panel == filter_value)
            
            logger.info(f"Filter applied: access_to_admin_panel == {filter_value}")
        
        # Get total count
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        stmt = stmt.order_by(WalletUser.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query - handle case where is_verified column doesn't exist in DB
        try:
            result = await db.execute(stmt)
            users = result.scalars().all()
        except Exception as e:
            # If error is related to missing column, log and re-raise with helpful message
            error_str = str(e).lower()
            if 'is_verified' in error_str or ('column' in error_str and 'does not exist' in error_str):
                raise HTTPException(
                    status_code=500,
                    detail="Database migration required: Please run 'alembic upgrade head' to add is_verified column to wallet_users table"
                )
            raise
        
        # Convert users to response, handling missing is_verified field
        user_items = []
        for user in users:
            try:
                is_verified = user.is_verified
            except (AttributeError, KeyError):
                is_verified = False
            
            # Get balance_usdt safely
            balance_usdt = getattr(user, 'balance_usdt', 0.0)
            if balance_usdt is None:
                balance_usdt = 0.0
            else:
                # Convert Decimal to float if needed
                balance_usdt = float(balance_usdt)
            
            user_dict = {
                "id": user.id,
                "wallet_address": user.wallet_address,
                "blockchain": user.blockchain,
                "did": user.did,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "access_to_admin_panel": user.access_to_admin_panel,
                "is_verified": is_verified,
                "balance_usdt": balance_usdt,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
            user_items.append(WalletUserItem(**user_dict))
        
        return WalletUserList(
            users=user_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching wallet users: {str(e)}"
        )


@router.get("/{user_id}", response_model=WalletUserItem)
async def get_wallet_user(
    user_id: int,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get single wallet user by ID
    
    Args:
        user_id: User ID
        db: Database session
        admin: Admin authentication
        
    Returns:
        Wallet user information
    """
    try:
        result = await db.execute(
            select(WalletUser).where(WalletUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        
        # Handle missing is_verified field
        try:
            is_verified = user.is_verified
        except (AttributeError, KeyError):
            is_verified = False
        
        # Get balance_usdt safely
        balance_usdt = getattr(user, 'balance_usdt', 0.0)
        if balance_usdt is None:
            balance_usdt = 0.0
        else:
            # Convert Decimal to float if needed
            balance_usdt = float(balance_usdt)
        
        user_dict = {
            "id": user.id,
            "wallet_address": user.wallet_address,
            "blockchain": user.blockchain,
            "did": user.did,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "access_to_admin_panel": user.access_to_admin_panel,
            "is_verified": is_verified,
            "balance_usdt": balance_usdt,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        return WalletUserItem(**user_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching wallet user: {str(e)}"
        )


@router.post("", response_model=WalletUserItem)
async def create_wallet_user(
    request: CreateWalletUserRequest,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Create new wallet user
    
    Args:
        request: User creation request
        db: Database session
        admin: Admin authentication
        
    Returns:
        Created wallet user
    """
    try:
        # Check if wallet address already exists
        result = await db.execute(
            select(WalletUser).where(WalletUser.wallet_address == request.wallet_address)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail=f"User with wallet address {request.wallet_address} already exists"
            )
        
        # Create new user
        new_user = WalletUser(
            wallet_address=request.wallet_address,
            blockchain=request.blockchain,
            nickname=request.nickname,
            access_to_admin_panel=request.access_to_admin_panel,
            is_verified=request.is_verified
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Handle missing is_verified field
        # Get balance_usdt safely
        balance_usdt = getattr(new_user, 'balance_usdt', 0.0)
        if balance_usdt is None:
            balance_usdt = 0.0
        else:
            # Convert Decimal to float if needed
            balance_usdt = float(balance_usdt)
        
        user_dict = {
            "id": new_user.id,
            "wallet_address": new_user.wallet_address,
            "blockchain": new_user.blockchain,
            "did": new_user.did,
            "nickname": new_user.nickname,
            "avatar": new_user.avatar,
            "access_to_admin_panel": new_user.access_to_admin_panel,
            "is_verified": getattr(new_user, 'is_verified', False),  # Handle missing field
            "balance_usdt": balance_usdt,
            "created_at": new_user.created_at,
            "updated_at": new_user.updated_at,
        }
        return WalletUserItem(**user_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating wallet user: {str(e)}"
        )


@router.put("/{user_id}", response_model=WalletUserItem)
async def update_wallet_user(
    user_id: int,
    request: UpdateWalletUserRequest,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Update wallet user
    
    Args:
        user_id: User ID
        request: Update request
        db: Database session
        admin: Admin authentication
        
    Returns:
        Updated wallet user
    """
    try:
        result = await db.execute(
            select(WalletUser).where(WalletUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        
        # Update fields
        if request.nickname is not None:
            user.nickname = request.nickname
        if request.blockchain is not None:
            user.blockchain = request.blockchain
        if request.is_verified is not None:
            # Try to set is_verified field (migration might not be applied)
            try:
                user.is_verified = request.is_verified
            except (AttributeError, KeyError):
                # Field doesn't exist in database yet, skip update
                pass
        if request.access_to_admin_panel is not None:
            user.access_to_admin_panel = request.access_to_admin_panel
        
        await db.commit()
        await db.refresh(user)
        
        # Handle missing is_verified field
        try:
            is_verified = user.is_verified
        except (AttributeError, KeyError):
            is_verified = False
        
        # Get balance_usdt safely
        balance_usdt = getattr(user, 'balance_usdt', 0.0)
        if balance_usdt is None:
            balance_usdt = 0.0
        else:
            # Convert Decimal to float if needed
            balance_usdt = float(balance_usdt)
        
        user_dict = {
            "id": user.id,
            "wallet_address": user.wallet_address,
            "blockchain": user.blockchain,
            "did": user.did,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "access_to_admin_panel": user.access_to_admin_panel,
            "is_verified": is_verified,
            "balance_usdt": balance_usdt,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        return WalletUserItem(**user_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating wallet user: {str(e)}"
        )


@router.delete("/{user_id}", response_model=ChangeResponse)
async def delete_wallet_user(
    user_id: int,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Delete wallet user
    
    Args:
        user_id: User ID
        db: Database session
        admin: Admin authentication
        
    Returns:
        Success status
    """
    try:
        result = await db.execute(
            select(WalletUser).where(WalletUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        
        await db.delete(user)
        await db.commit()
        
        return ChangeResponse(
            success=True,
            message=f"User {user.nickname} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting wallet user: {str(e)}"
        )


# === PUBLIC PROFILE ENDPOINTS ===

@profile_router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user = Depends(get_current_tron_user),
    db: DbDepends = None
):
    """
    Get profile of the current authenticated user
    
    Returns:
        User profile information
    """
    try:
        wallet_address = current_user.wallet_address
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Handle missing is_verified field
        try:
            is_verified = user.is_verified
        except (AttributeError, KeyError):
            is_verified = False
        
        # Get balance_usdt safely
        balance_usdt = getattr(user, 'balance_usdt', 0.0)
        if balance_usdt is None:
            balance_usdt = 0.0
        else:
            # Convert Decimal to float if needed
            balance_usdt = float(balance_usdt)
        
        return ProfileResponse(
            wallet_address=user.wallet_address,
            blockchain=user.blockchain,
            did=user.did,
            nickname=user.nickname,
            avatar=user.avatar,
            access_to_admin_panel=user.access_to_admin_panel,
            is_verified=is_verified,
            balance_usdt=balance_usdt,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching profile: {str(e)}"
        )


@profile_router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user = Depends(get_current_tron_user),
    db: DbDepends = None
):
    """
    Update profile of the current authenticated user
    
    Can update nickname and/or avatar.
    Nicknames must be unique across all users.
    Avatar should be in base64 data URI format (data:image/...)
    
    Args:
        request: Profile update request
        
    Returns:
        Updated user profile
    """
    try:
        wallet_address = current_user.wallet_address
        
        # Update profile using service method
        user = await WalletUserService.update_profile(
            wallet_address=wallet_address,
            nickname=request.nickname,
            avatar=request.avatar,
            db=db
        )
        
        # Handle missing is_verified field
        try:
            is_verified = user.is_verified
        except (AttributeError, KeyError):
            is_verified = False
        
        # Get balance_usdt safely
        balance_usdt = getattr(user, 'balance_usdt', 0.0)
        if balance_usdt is None:
            balance_usdt = 0.0
        else:
            # Convert Decimal to float if needed
            balance_usdt = float(balance_usdt)
        
        return ProfileResponse(
            wallet_address=user.wallet_address,
            blockchain=user.blockchain,
            did=user.did,
            nickname=user.nickname,
            avatar=user.avatar,
            access_to_admin_panel=user.access_to_admin_panel,
            is_verified=is_verified,
            balance_usdt=balance_usdt,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating profile: {str(e)}"
        )


@profile_router.get("/me/billing", response_model=BillingList)
async def get_my_billing_history(
    page: int = 1,
    page_size: int = 20,
    current_user = Depends(get_current_tron_user),
    db: DbDepends = None
):
    """
    Get billing transaction history for the current authenticated user
    
    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of billing transactions with pagination info
    """
    try:
        wallet_address = current_user.wallet_address
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Build query
        stmt = select(Billing).where(Billing.wallet_user_id == user.id)
        count_stmt = select(func.count(Billing.id)).where(Billing.wallet_user_id == user.id)
        
        # Get total count
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        stmt = stmt.order_by(desc(Billing.created_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await db.execute(stmt)
        transactions = result.scalars().all()
        
        # Convert to response
        transaction_items = [
            BillingItem(
                id=t.id,
                wallet_user_id=t.wallet_user_id,
                usdt_amount=float(t.usdt_amount),
                created_at=t.created_at
            )
            for t in transactions
        ]
        
        return BillingList(
            transactions=transaction_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching billing history: {str(e)}"
        )


# Public endpoint for DIDDoc (no admin auth required) - must be before generic /user/{identifier}
@profile_router.get("/user/{user_id}/did-doc")
async def get_user_did_doc_public(
    user_id: int,
    db: DbDepends
):
    """
    Get DID Document for a user with proofs, ratings, and other information (public endpoint)
    
    Args:
        user_id: Wallet user ID
        db: Database session
        
    Returns:
        DID Document with user information, proofs, and ratings
    """
    try:
        if db is None:
            raise HTTPException(
                status_code=500,
                detail="Database session not available"
            )
        
        return await WalletUserService.get_did_document(user_id, db)
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error fetching user DID Document: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user DID Document: {str(e)}"
        )


# Public endpoint for getting user profile by user_id or DID
@profile_router.get("/user/{identifier}")
async def get_user_profile_public(
    identifier: str,
    db: DbDepends
):
    """
    Get user profile by user_id or DID (public endpoint)
    
    Args:
        identifier: User ID (integer) or DID (string starting with 'did:')
        db: Database session
        
    Returns:
        User profile information
    """
    try:
        # Determine if identifier is user_id or DID
        if identifier.startswith("did:"):
            # Search by DID
            result = await db.execute(
                select(WalletUser).where(WalletUser.did == identifier)
            )
        else:
            # Try to parse as user_id (integer)
            try:
                user_id = int(identifier)
                result = await db.execute(
                    select(WalletUser).where(WalletUser.id == user_id)
                )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid identifier: must be a user ID (integer) or DID (starting with 'did:')"
                )
        
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with identifier '{identifier}' not found"
            )
        
        # Handle missing is_verified field
        try:
            is_verified = user.is_verified
        except (AttributeError, KeyError):
            is_verified = False
        
        # Get balance_usdt safely
        balance_usdt = getattr(user, 'balance_usdt', 0.0)
        if balance_usdt is None:
            balance_usdt = 0.0
        else:
            # Convert Decimal to float if needed
            balance_usdt = float(balance_usdt)
        
        return ProfileResponse(
            wallet_address=user.wallet_address,
            blockchain=user.blockchain,
            did=user.did,
            nickname=user.nickname,
            avatar=user.avatar,
            access_to_admin_panel=user.access_to_admin_panel,
            is_verified=is_verified,
            balance_usdt=balance_usdt,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user profile: {str(e)}"
        )


@router.get("/{user_id}/did-doc")
async def get_user_did_doc(
    user_id: int,
    db: DbDepends
):
    """
    Get DID Document for a user with proofs, ratings, and other information
    
    Args:
        user_id: Wallet user ID
        db: Database session
        admin: Admin authentication (optional for public access)
        
    Returns:
        DID Document with user information, proofs, and ratings
    """
    try:
        return await WalletUserService.get_did_document(user_id, db)
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error fetching user DID Document: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user DID Document: {str(e)}"
        )

