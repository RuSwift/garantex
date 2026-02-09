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


class PermissionKey(BaseModel):
    """Permission key with address and weight"""
    address: str = Field(..., description="Wallet address")
    weight: int = Field(..., ge=1, description="Key weight (must be >= 1)")


class UpdatePermissionsRequest(BaseModel):
    """Request to update wallet permissions"""
    threshold: int = Field(..., ge=1, description="Required threshold (sum of weights)")
    keys: List[PermissionKey] = Field(..., min_length=1, description="List of keys with addresses and weights")
    permission_name: str = Field(default="multisig", description="Permission name")
    operations: str = Field(
        default="c0000000000000000000000000000000000000000000000000000000000000000",
        description="Operations hex string (default: only token transfers)"
    )


class UpdatePermissionsResponse(BaseModel):
    """Response for update permissions transaction"""
    success: bool = Field(..., description="Success status")
    tx_id: str = Field(..., description="Transaction ID")
    raw_data_hex: str = Field(..., description="Raw transaction data hex")
    message: str = Field(..., description="Response message")

