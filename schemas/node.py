"""
Схемы для API инициализации ноды
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


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

