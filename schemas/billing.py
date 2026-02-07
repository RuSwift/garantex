"""
Schemas for billing transactions
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BillingItem(BaseModel):
    """Single billing transaction"""
    id: int = Field(..., description="Transaction ID")
    wallet_user_id: int = Field(..., description="Wallet user ID")
    usdt_amount: float = Field(..., description="USDT amount: positive for deposit, negative for withdrawal")
    created_at: datetime = Field(..., description="Transaction timestamp")
    
    class Config:
        from_attributes = True


class BillingList(BaseModel):
    """List of billing transactions with pagination"""
    transactions: List[BillingItem] = Field(..., description="List of transactions")
    total: int = Field(..., description="Total number of transactions")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class CreateBillingRequest(BaseModel):
    """Request to create billing transaction"""
    usdt_amount: float = Field(..., description="USDT amount: positive for deposit, negative for withdrawal")


class BillingSearchRequest(BaseModel):
    """Request to search billing transactions"""
    wallet_user_id: Optional[int] = Field(None, description="Filter by wallet user ID")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")

