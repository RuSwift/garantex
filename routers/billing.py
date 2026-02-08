"""
Router for billing transactions management API
"""
from fastapi import APIRouter, HTTPException, Depends
from dependencies import RequireAdminDepends, DbDepends
from schemas.billing import (
    BillingItem,
    BillingList,
    CreateBillingRequest,
    BillingSearchRequest
)
from schemas.node import ChangeResponse
from db.models import Billing, WalletUser
from sqlalchemy import select, func, desc
from decimal import Decimal

router = APIRouter(
    prefix="/api/admin/billing",
    tags=["billing"]
)


@router.post("/users/{user_id}/transactions", response_model=BillingItem)
async def create_billing_transaction(
    user_id: int,
    request: CreateBillingRequest,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Create billing transaction (deposit or withdrawal) for a user
    
    Args:
        user_id: Wallet user ID
        request: Transaction request (positive amount for deposit, negative for withdrawal)
        db: Database session
        admin: Admin authentication
        
    Returns:
        Created billing transaction
    """
    try:
        # Check if user exists
        result = await db.execute(
            select(WalletUser).where(WalletUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        
        # Validate amount
        amount = Decimal(str(request.usdt_amount))
        if amount == 0:
            raise HTTPException(
                status_code=400,
                detail="Amount cannot be zero"
            )
        
        # Get current balance
        current_balance = user.balance_usdt or Decimal('0')
        
        # Calculate new balance
        new_balance = current_balance + amount
        
        # Check if withdrawal would result in negative balance
        if new_balance < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Current balance: {current_balance}, requested: {abs(amount)}"
            )
        
        # Create billing transaction
        billing = Billing(
            wallet_user_id=user_id,
            usdt_amount=amount
        )
        
        # Update user balance
        user.balance_usdt = new_balance
        
        db.add(billing)
        await db.commit()
        await db.refresh(billing)
        
        return BillingItem(
            id=billing.id,
            wallet_user_id=billing.wallet_user_id,
            usdt_amount=float(billing.usdt_amount),
            created_at=billing.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating billing transaction: {str(e)}"
        )


@router.get("/users/{user_id}/transactions", response_model=BillingList)
async def get_user_billing_history(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    db: DbDepends = None,
    admin: RequireAdminDepends = None
):
    """
    Get billing transaction history for a user
    
    Args:
        user_id: Wallet user ID
        page: Page number (starting from 1)
        page_size: Number of items per page
        db: Database session
        admin: Admin authentication
        
    Returns:
        List of billing transactions with pagination info
    """
    try:
        # Check if user exists
        result = await db.execute(
            select(WalletUser).where(WalletUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with ID {user_id} not found"
            )
        
        # Build query
        stmt = select(Billing).where(Billing.wallet_user_id == user_id)
        count_stmt = select(func.count(Billing.id)).where(Billing.wallet_user_id == user_id)
        
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


@router.get("/transactions", response_model=BillingList)
async def list_all_billing_transactions(
    page: int = 1,
    page_size: int = 20,
    user_id: int = None,
    db: DbDepends = None,
    admin: RequireAdminDepends = None
):
    """
    Get all billing transactions with optional user filter
    
    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page
        user_id: Optional filter by wallet user ID
        db: Database session
        admin: Admin authentication
        
    Returns:
        List of billing transactions with pagination info
    """
    try:
        # Build query
        stmt = select(Billing)
        count_stmt = select(func.count(Billing.id))
        
        # Apply user filter if provided
        if user_id:
            stmt = stmt.where(Billing.wallet_user_id == user_id)
            count_stmt = count_stmt.where(Billing.wallet_user_id == user_id)
        
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
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching billing transactions: {str(e)}"
        )


