"""
Router for Escrow API endpoints
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import DbDepends
from routers.auth import get_current_tron_user, UserInfo
from db.models import EscrowModel, EscrowTxnModel, Deal
from services.deals.service import DealsService
from ledgers import get_user_did

router = APIRouter(
    prefix="/api/escrow",
    tags=["escrow"]
)


class EscrowLogEntry(BaseModel):
    """Entry in escrow transaction log"""
    id: int = Field(..., description="Log entry ID")
    escrow_id: int = Field(..., description="Escrow ID")
    type: str = Field(..., description="Type: 'txn' for transaction, 'event' for event")
    comment: str = Field(..., description="Comment describing the transaction or event")
    txn: Optional[Dict[str, Any]] = Field(None, description="Transaction or event data (JSONB)")
    counter: int = Field(1, description="Counter for duplicate events")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")


class EscrowLogsResponse(BaseModel):
    """Response for escrow logs"""
    escrow_id: int = Field(..., description="Escrow ID")
    logs: List[EscrowLogEntry] = Field(..., description="List of log entries")


@router.get("/{escrow_id}/logs", response_model=EscrowLogsResponse)
async def get_escrow_logs(
    escrow_id: int,
    db: DbDepends = None,
    current_user: Optional[UserInfo] = Depends(get_current_tron_user)
):
    """
    Get escrow transaction logs
    
    Args:
        escrow_id: Escrow ID
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        Escrow logs response
        
    Raises:
        HTTPException: If escrow not found or user doesn't have access
    """
    try:
        # Get escrow
        stmt = select(EscrowModel).where(EscrowModel.id == escrow_id)
        result = await db.execute(stmt)
        escrow = result.scalar_one_or_none()
        
        if not escrow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Escrow not found"
            )
        
        # Check if user has access to this escrow
        # User must be a participant (sender, receiver, or arbiter) in a deal with this escrow
        if current_user:
            user_did = get_user_did(current_user.wallet_address, 'tron')
            
            # Check if user is involved in any deal with this escrow
            deal_stmt = select(Deal).where(
                Deal.escrow_id == escrow_id
            ).where(
                (Deal.sender_did == user_did) |
                (Deal.receiver_did == user_did) |
                (Deal.arbiter_did == user_did)
            )
            deal_result = await db.execute(deal_stmt)
            deal = deal_result.scalar_one_or_none()
            
            if not deal:
                # Also check if user is the owner of the escrow
                if escrow.owner_did != user_did:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You don't have permission to view this escrow"
                    )
        
        # Get escrow transaction log
        log_stmt = select(EscrowTxnModel).where(EscrowTxnModel.escrow_id == escrow_id)
        log_result = await db.execute(log_stmt)
        escrow_txn = log_result.scalar_one_or_none()
        
        logs = []
        if escrow_txn:
            # Convert to response format
            # Ensure counter is always present (default to 1 if None)
            counter_value = escrow_txn.counter if escrow_txn.counter is not None else 1
            logs.append(EscrowLogEntry(
                id=escrow_txn.id,
                escrow_id=escrow_txn.escrow_id,
                type=escrow_txn.type,
                comment=escrow_txn.comment,
                txn=escrow_txn.txn,
                counter=counter_value,
                created_at=escrow_txn.created_at.isoformat() if escrow_txn.created_at else "",
                updated_at=escrow_txn.updated_at.isoformat() if escrow_txn.updated_at else ""
            ))
        
        return EscrowLogsResponse(
            escrow_id=escrow_id,
            logs=logs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting escrow logs: {str(e)}"
        )

