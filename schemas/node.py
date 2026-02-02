"""
Схемы для API инициализации ноды
"""
from pydantic import BaseModel, Field
from typing import Optional


class NodeInitRequest(BaseModel):
    """Запрос на инициализацию ноды с мнемонической фразой"""
    mnemonic: str = Field(..., description="Мнемоническая фраза для инициализации ноды")


class NodeInitPemRequest(BaseModel):
    """Запрос на инициализацию ноды с PEM ключом"""
    pem_data: str = Field(..., description="PEM данные (строка)")
    password: Optional[str] = Field(None, description="Пароль для расшифровки PEM (опционально)")

