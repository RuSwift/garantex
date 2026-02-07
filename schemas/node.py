"""
Схемы для API инициализации ноды и управления админом
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class NodeInitRequest(BaseModel):
    """Запрос на инициализацию ноды с мнемонической фразой"""
    mnemonic: str = Field(..., description="Мнемоническая фраза для инициализации ноды")


class NodeInitPemRequest(BaseModel):
    """Запрос на инициализацию ноды с PEM ключом"""
    pem_data: str = Field(..., description="PEM данные (строка)")
    password: Optional[str] = Field(None, description="Пароль для расшифровки PEM (опционально)")


class NodeInitResponse(BaseModel):
    """Ответ на запрос инициализации ноды"""
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    did: str = Field(..., description="DID ноды")
    address: Optional[str] = Field(None, description="Ethereum адрес (если используется ETH ключ)")
    key_type: str = Field(..., description="Тип ключа: mnemonic или pem")
    public_key: str = Field(..., description="Публичный ключ в hex формате")
    did_document: Dict[str, Any] = Field(..., description="DID документ")


# ====================
# Admin Schemas (New Architecture)
# ====================

class SetPasswordRequest(BaseModel):
    """Request to set/update admin password"""
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")


class ChangePasswordRequest(BaseModel):
    """Request to change admin password"""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")


class AdminInfoResponse(BaseModel):
    """Response with admin information"""
    id: int = Field(..., description="Admin ID (always 1)")
    has_password: bool = Field(..., description="Whether password is configured")
    username: Optional[str] = Field(None, description="Admin username (if password configured)")
    tron_addresses_count: int = Field(..., description="Number of active TRON addresses")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class TronAddressItem(BaseModel):
    """Single TRON admin address"""
    id: int = Field(..., description="Address ID")
    tron_address: str = Field(..., description="TRON address")
    label: Optional[str] = Field(None, description="Optional label")
    is_active: bool = Field(..., description="Whether address is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class TronAddressList(BaseModel):
    """List of TRON admin addresses"""
    addresses: List[TronAddressItem] = Field(..., description="List of TRON addresses")


class AddTronAddressRequest(BaseModel):
    """Request to add TRON address"""
    tron_address: str = Field(..., description="TRON address to add")
    label: Optional[str] = Field(None, description="Optional label for this address")


class UpdateTronAddressRequest(BaseModel):
    """Request to update TRON address"""
    tron_address: Optional[str] = Field(None, description="New TRON address (optional)")
    label: Optional[str] = Field(None, description="New label (optional)")


class ToggleTronAddressRequest(BaseModel):
    """Request to toggle TRON address active status"""
    is_active: bool = Field(..., description="Active status")


class ChangeResponse(BaseModel):
    """Generic response for change operations"""
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Status message")


class AdminConfiguredResponse(BaseModel):
    """Response for admin configured check"""
    configured: bool = Field(..., description="Whether admin is configured")
    has_password: bool = Field(False, description="Whether password is configured")
    tron_addresses_count: int = Field(0, description="Number of TRON addresses")


# ====================
# ServiceEndpoint Schemas
# ====================

class SetServiceEndpointRequest(BaseModel):
    """Request to set service endpoint"""
    service_endpoint: str = Field(..., description="Service endpoint URL (e.g., https://node.example.com/endpoint)")


class ServiceEndpointResponse(BaseModel):
    """Response with service endpoint information"""
    service_endpoint: Optional[str] = Field(None, description="Current service endpoint URL")
    configured: bool = Field(..., description="Whether service endpoint is configured")


class TestServiceEndpointRequest(BaseModel):
    """Request to test service endpoint availability"""
    service_endpoint: str = Field(..., description="Service endpoint URL to test")


class TestServiceEndpointResponse(BaseModel):
    """Response for service endpoint test"""
    success: bool = Field(..., description="Whether endpoint is accessible")
    status_code: Optional[int] = Field(None, description="HTTP status code received")
    message: str = Field(..., description="Test result message")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")


# ====================
# Admin Authentication Schemas
# ====================

class AdminLoginRequest(BaseModel):
    """Request for admin password authentication"""
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")


class AdminLoginResponse(BaseModel):
    """Response for admin authentication"""
    success: bool = Field(..., description="Login success status")
    token: Optional[str] = Field(None, description="JWT token for authentication")
    message: Optional[str] = Field(None, description="Status message")


class AdminTronNonceRequest(BaseModel):
    """Request for TRON nonce"""
    tron_address: str = Field(..., description="TRON wallet address")


class AdminTronNonceResponse(BaseModel):
    """Response with nonce for TRON signing"""
    nonce: str = Field(..., description="Nonce to sign")
    message: str = Field(..., description="Message to sign")


class AdminTronVerifyRequest(BaseModel):
    """Request to verify TRON signature"""
    tron_address: str = Field(..., description="TRON wallet address")
    signature: str = Field(..., description="Signed message")
    message: str = Field(..., description="Original message")

