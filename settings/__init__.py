"""
Настройки приложения с использованием pydantic_settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional


class DatabaseSettings(BaseSettings):
    """Настройки подключения к PostgreSQL"""
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Настройки подключения
    host: str = Field(
        default="localhost",
        description="Хост базы данных PostgreSQL"
    )
    
    port: int = Field(
        default=5432,
        description="Порт базы данных PostgreSQL"
    )
    
    user: str = Field(
        default="postgres",
        description="Имя пользователя базы данных"
    )
    
    password: SecretStr = Field(
        default=SecretStr(""),
        description="Пароль базы данных"
    )
    
    database: str = Field(
        default="garantex",
        description="Имя базы данных"
    )
    
    # Дополнительные настройки
    pool_size: int = Field(
        default=5,
        description="Размер пула соединений"
    )
    
    max_overflow: int = Field(
        default=10,
        description="Максимальное количество переполнений пула"
    )
    
    pool_timeout: int = Field(
        default=30,
        description="Таймаут ожидания соединения из пула (секунды)"
    )
    
    echo: bool = Field(
        default=False,
        description="Логировать SQL запросы"
    )
    
    @property
    def url(self) -> str:
        """Возвращает URL подключения к базе данных"""
        password_value = self.password.get_secret_value() if self.password else ""
        return f"postgresql://{self.user}:{password_value}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_url(self) -> str:
        """Возвращает async URL подключения к базе данных"""
        password_value = self.password.get_secret_value() if self.password else ""
        return f"postgresql+asyncpg://{self.user}:{password_value}@{self.host}:{self.port}/{self.database}"


class MnemonicSettings(BaseSettings):
    """Настройки для хранения mnemonic phrase"""
    
    model_config = SettingsConfigDict(
        env_prefix="MNEMONIC_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    phrase: Optional[SecretStr] = Field(
        default=None,
        description="Мнемоническая фраза для генерации ключей (опционально)"
    )
    
    encrypted_phrase: Optional[SecretStr] = Field(
        default=None,
        description="Зашифрованная мнемоническая фраза (опционально)"
    )
    
    storage_path: Optional[str] = Field(
        default=None,
        description="Путь к файлу для хранения мнемонической фразы (опционально)"
    )


class Settings(BaseSettings):
    """Основные настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Настройки приложения
    app_name: str = Field(
        default="Garantex API",
        description="Название приложения"
    )
    
    app_version: str = Field(
        default="1.0.0",
        description="Версия приложения"
    )
    
    debug: bool = Field(
        default=False,
        description="Режим отладки"
    )
    
    # Настройки базы данных
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    
    # Настройки мнемонической фразы
    mnemonic: MnemonicSettings = Field(default_factory=MnemonicSettings)


# Создаем глобальный экземпляр настроек
settings = Settings()

# Экспортируем для удобства
__all__ = [
    "Settings",
    "DatabaseSettings",
    "MnemonicSettings",
    "settings"
]

