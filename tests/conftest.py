"""
Централизованная конфигурация pytest для всех тестов
Использует реальный PostgreSQL из docker-compose
"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, text
from httpx import AsyncClient, ASGITransport

from db import Base, get_db
from node import app
from settings import DatabaseSettings, Settings


# Параметры тестовой базы данных
TEST_DB_NAME = "garantex_test"


@pytest.fixture(scope="session")
def event_loop():
    """
    Создает event loop для всей сессии тестов
    Необходимо для async фикстур с scope="session"
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db_settings():
    """
    Возвращает настройки для тестовой БД
    Использует параметры из .env, но с другим именем базы данных
    """
    db_settings = DatabaseSettings()
    return DatabaseSettings(
        host=db_settings.host,
        port=db_settings.port,
        user=db_settings.user,
        password=db_settings.password,
        database=TEST_DB_NAME,
        echo=False
    )


@pytest.fixture(scope="session", autouse=True)
def create_test_database(test_db_settings):
    """
    Создает тестовую базу данных перед запуском тестов
    Удаляет её после завершения всех тестов
    """
    # Подключаемся к postgres database для создания тестовой БД
    db_settings = DatabaseSettings()
    admin_url = f"postgresql://{db_settings.user}:{db_settings.password.get_secret_value()}@{db_settings.host}:{db_settings.port}/postgres"
    
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    
    with engine.connect() as conn:
        # Закрываем все активные соединения к тестовой БД (если есть)
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
            AND pid <> pg_backend_pid()
        """))
        
        # Удаляем тестовую БД если она существует
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        
        # Создаем новую тестовую БД
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    
    engine.dispose()
    
    # Применяем миграции к тестовой БД
    # Используем alembic для этого
    import os
    original_db_database = os.environ.get("DB_DATABASE")
    os.environ["DB_DATABASE"] = TEST_DB_NAME
    
    try:
        from alembic import command
        from alembic.config import Config
        
        alembic_cfg = Config("alembic.ini")
        # Устанавливаем URL для тестовой БД
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_settings.url)
        command.upgrade(alembic_cfg, "head")
    finally:
        # Восстанавливаем оригинальное значение
        if original_db_database:
            os.environ["DB_DATABASE"] = original_db_database
        else:
            os.environ.pop("DB_DATABASE", None)
    
    yield
    
    # Удаляем тестовую БД после всех тестов
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        # Закрываем все активные соединения
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
            AND pid <> pg_backend_pid()
        """))
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    engine.dispose()


@pytest.fixture(scope="session")
async def db_engine(test_db_settings):
    """
    Создает async engine для тестовой БД
    Используется на протяжении всей сессии тестов
    """
    engine = create_async_engine(
        test_db_settings.async_url,
        echo=False,
        pool_pre_ping=True
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Создает новую сессию БД для каждого теста
    После теста очищает все таблицы (кроме alembic_version)
    """
    TestSessionLocal = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with TestSessionLocal() as session:
        yield session
    
    # Очищаем все таблицы после каждого теста
    async with db_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE node_settings CASCADE"))
        await conn.execute(text("TRUNCATE TABLE admin_users CASCADE"))
        await conn.execute(text("TRUNCATE TABLE admin_tron_addresses CASCADE"))
        await conn.execute(text("TRUNCATE TABLE storage CASCADE"))
        await conn.execute(text("TRUNCATE TABLE connections CASCADE"))
        # Добавьте другие таблицы если они есть
        # Не трогаем alembic_version


@pytest.fixture
async def test_client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """
    Создает тестовый HTTP клиент с переопределенной БД
    """
    async def override_get_db():
        yield test_db
    
    from dependencies.settings import get_settings
    async def override_get_settings():
        return Settings()
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# Дополнительные фикстуры для тестов
@pytest.fixture
def valid_mnemonic():
    """Генерирует валидную мнемоническую фразу"""
    from mnemonic import Mnemonic
    mnemo = Mnemonic("english")
    return mnemo.generate(strength=128)


@pytest.fixture
def test_secret():
    """Секретный ключ для тестов"""
    return "test-secret-key-for-encryption-12345678"


@pytest.fixture
def set_test_secret(test_secret, monkeypatch):
    """Устанавливает тестовый секретный ключ в окружение"""
    monkeypatch.setenv("SECRET", test_secret)
    return test_secret

