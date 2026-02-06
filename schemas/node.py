"""
Схемы для API инициализации ноды
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
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


class RootCredentialsRequest(BaseModel):
    """Request to set root admin credentials"""
    method: str = Field(..., description="Auth method: 'password' or 'tron'")
    username: Optional[str] = Field(None, description="Admin username (for password method)")
    password: Optional[str] = Field(None, description="Admin password (for password method)")
    tron_address: Optional[str] = Field(None, description="TRON address (for tron method)")


class RootCredentialsResponse(BaseModel):
    """Response after setting root credentials"""
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Status message")
    auth_method: str = Field(..., description="Authentication method configured")


class AdminLoginRequest(BaseModel):
    """Request to login as admin"""
    method: str = Field(..., description="Auth method: 'password' or 'tron'")
    username: Optional[str] = Field(None, description="Admin username (for password method)")
    password: Optional[str] = Field(None, description="Admin password (for password method)")
    tron_token: Optional[str] = Field(None, description="TRON auth JWT token (for tron method)")


class AdminLoginResponse(BaseModel):
    """Response after admin login"""
    success: bool = Field(..., description="Success status")
    token: str = Field(..., description="Admin session JWT token")
    auth_method: str = Field(..., description="Authentication method used")


class AdminInfoResponse(BaseModel):
    """Response with admin information"""
    id: int = Field(..., description="Admin ID")
    auth_method: str = Field(..., description="Auth method: password or tron")
    username: Optional[str] = Field(None, description="Admin username")
    tron_address: Optional[str] = Field(None, description="TRON address")
    is_active: bool = Field(..., description="Whether admin is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class ChangePasswordRequest(BaseModel):
    """Request to change admin password"""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")


class ChangeTronAddressRequest(BaseModel):
    """Request to change admin TRON address"""
    new_tron_address: str = Field(..., description="New TRON address")


class ChangeResponse(BaseModel):
    """Response after changing credentials"""
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Status message")
