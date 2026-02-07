"""
Router for WalletUser management API
"""
from fastapi import APIRouter, HTTPException
from dependencies import RequireAdminDepends, DbDepends
from schemas.node import (
    WalletUserItem, 
    WalletUserList, 
    CreateWalletUserRequest,
    UpdateWalletUserRequest,
    ChangeResponse
)
from db.models import WalletUser
from sqlalchemy import select, func, or_

router = APIRouter(
    prefix="/api/admin/wallet-users",
    tags=["wallet-users"]
)


@router.get("", response_model=WalletUserList)
async def list_wallet_users(
    page: int = 1,
    page_size: int = 20,
    query: str = None,
    blockchain: str = None,
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
        
        # Get total count
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        stmt = stmt.order_by(WalletUser.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        return WalletUserList(
            users=[WalletUserItem.model_validate(user) for user in users],
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
        
        return WalletUserItem.model_validate(user)
        
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
            nickname=request.nickname
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return WalletUserItem.model_validate(new_user)
        
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
        
        await db.commit()
        await db.refresh(user)
        
        return WalletUserItem.model_validate(user)
        
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

