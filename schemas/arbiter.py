"""
Schemas for arbiter address management API
"""
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class CreateArbiterAddressRequest(BaseModel):
    """Request to create a new arbiter address"""
    name: str = Field(..., description="Arbiter address name", max_length=255)
    mnemonic: str = Field(..., description="Mnemonic phrase for address generation")


class UpdateArbiterAddressNameRequest(BaseModel):
    """Request to update arbiter address name"""
    name: str = Field(..., description="New arbiter address name", max_length=255)


class ArbiterAddressResponse(BaseModel):
    """Response model for arbiter address"""
    id: int = Field(..., description="Arbiter address ID")
    name: str = Field(..., description="Arbiter address name")
    tron_address: str = Field(..., description="TRON address")
    ethereum_address: str = Field(..., description="Ethereum address")
    role: str = Field(None, description="Wallet role (arbiter or arbiter-backup)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    
    class Config:
        from_attributes = True


class ArbiterAddressListResponse(BaseModel):
    """Response model for arbiter address list"""
    addresses: List[ArbiterAddressResponse] = Field(..., description="List of arbiter addresses")
    total: int = Field(..., description="Total number of arbiter addresses")
