"""
Schemas for advertisement management
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AdvertisementBase(BaseModel):
    """Base advertisement schema"""
    name: str = Field(..., description="Display name for the advertisement", max_length=255)
    description: str = Field(..., description="Detailed description of the offer")
    fee: str = Field(..., description="Fee percentage (e.g. '2.5')", max_length=10)
    min_limit: int = Field(..., description="Minimum transaction limit in USDT", ge=0)
    max_limit: int = Field(..., description="Maximum transaction limit in USDT", ge=0)
    currency: str = Field(..., description="Currency code (USD, EUR, RUB, etc.)", max_length=10)


class CreateAdvertisementRequest(AdvertisementBase):
    """Request to create advertisement"""
    pass


class UpdateAdvertisementRequest(BaseModel):
    """Request to update advertisement"""
    name: Optional[str] = Field(None, description="Display name for the advertisement", max_length=255)
    description: Optional[str] = Field(None, description="Detailed description of the offer")
    fee: Optional[str] = Field(None, description="Fee percentage (e.g. '2.5')", max_length=10)
    min_limit: Optional[int] = Field(None, description="Minimum transaction limit in USDT", ge=0)
    max_limit: Optional[int] = Field(None, description="Maximum transaction limit in USDT", ge=0)
    currency: Optional[str] = Field(None, description="Currency code (USD, EUR, RUB, etc.)", max_length=10)
    is_active: Optional[bool] = Field(None, description="Whether the advertisement is active")
    escrow_enabled: Optional[bool] = Field(None, description="Whether escrow deals are enabled")


class AdvertisementResponse(AdvertisementBase):
    """Response model for advertisement"""
    id: int = Field(..., description="Advertisement ID")
    user_id: int = Field(..., description="Owner user ID")
    is_active: bool = Field(..., description="Whether the advertisement is active")
    is_verified: bool = Field(..., description="Whether the advertisement is verified by admin")
    escrow_enabled: bool = Field(False, description="Whether escrow deals are enabled")
    user_is_verified: bool = Field(False, description="Whether the user (owner) is verified (document verification)")
    rating: Optional[str] = Field(None, description="User rating (e.g. '4.9')")
    deals_count: int = Field(..., description="Number of completed deals")
    owner_nickname: Optional[str] = Field(None, description="Owner's nickname")
    owner_avatar: Optional[str] = Field(None, description="Owner's avatar (base64 data URI)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    
    class Config:
        from_attributes = True


class AdvertisementListResponse(BaseModel):
    """List of advertisements with pagination"""
    advertisements: List[AdvertisementResponse] = Field(..., description="List of advertisements")
    total: int = Field(..., description="Total number of advertisements")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class AdvertisementSearchRequest(BaseModel):
    """Request to search advertisements"""
    query: Optional[str] = Field(None, description="Search query (name or description)")
    currency: Optional[str] = Field(None, description="Filter by currency")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verified status")
    min_amount: Optional[int] = Field(None, description="Minimum amount filter", ge=0)
    max_amount: Optional[int] = Field(None, description="Maximum amount filter", ge=0)
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")

