"""
Schemas for user profile management and wallet users
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WalletUserItem(BaseModel):
    """Single wallet user"""
    id: int = Field(..., description="User ID")
    wallet_address: str = Field(..., description="Wallet address")
    blockchain: str = Field(..., description="Blockchain type (tron, ethereum, bitcoin, etc.)")
    nickname: str = Field(..., description="User display name")
    avatar: Optional[str] = Field(None, description="User avatar in base64 format")
    access_to_admin_panel: bool = Field(False, description="Access to admin panel")
    is_verified: bool = Field(False, description="Whether the user is verified (document verification)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    
    class Config:
        from_attributes = True


class WalletUserList(BaseModel):
    """List of wallet users with pagination"""
    users: List[WalletUserItem] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class CreateWalletUserRequest(BaseModel):
    """Request to create wallet user"""
    wallet_address: str = Field(..., description="Wallet address")
    blockchain: str = Field(..., description="Blockchain type (tron, ethereum, etc.)")
    nickname: str = Field(..., description="User display name")


class UpdateWalletUserRequest(BaseModel):
    """Request to update wallet user (admin)"""
    nickname: Optional[str] = Field(None, description="New display name")
    blockchain: Optional[str] = Field(None, description="New blockchain type")
    is_verified: Optional[bool] = Field(None, description="Whether the user is verified")


class WalletUserSearchRequest(BaseModel):
    """Request to search wallet users"""
    query: Optional[str] = Field(None, description="Search query (wallet address or nickname)")
    blockchain: Optional[str] = Field(None, description="Filter by blockchain")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")


class UpdateProfileRequest(BaseModel):
    """Request model for updating user profile"""
    nickname: Optional[str] = Field(None, description="New nickname", max_length=100)
    avatar: Optional[str] = Field(None, description="Avatar in base64 format (data:image/...)")


class ProfileResponse(BaseModel):
    """Response model for user profile"""
    wallet_address: str = Field(..., description="Wallet address")
    blockchain: str = Field(..., description="Blockchain type")
    nickname: str = Field(..., description="User display name")
    avatar: Optional[str] = Field(None, description="User avatar in base64 format")
    access_to_admin_panel: bool = Field(..., description="Access to admin panel")
    is_verified: bool = Field(False, description="Whether the user is verified (document verification)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    
    class Config:
        from_attributes = True

