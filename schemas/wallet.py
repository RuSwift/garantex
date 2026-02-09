"""
Schemas for wallet management API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class CreateWalletRequest(BaseModel):
    """Request to create a new wallet"""
    name: str = Field(..., description="Wallet name", max_length=255)
    mnemonic: str = Field(..., description="Mnemonic phrase for wallet generation")


class UpdateWalletNameRequest(BaseModel):
    """Request to update wallet name"""
    name: str = Field(..., description="New wallet name", max_length=255)


class WalletResponse(BaseModel):
    """Response model for wallet"""
    id: int = Field(..., description="Wallet ID")
    name: str = Field(..., description="Wallet name")
    tron_address: str = Field(..., description="TRON address")
    ethereum_address: str = Field(..., description="Ethereum address")
    account_permissions: Optional[Dict[str, Any]] = Field(None, description="TRON account permissions from blockchain")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    
    class Config:
        from_attributes = True


class WalletListResponse(BaseModel):
    """Response model for wallet list"""
    wallets: List[WalletResponse] = Field(..., description="List of wallets")
    total: int = Field(..., description="Total number of wallets")

