"""
Тесты инициализации админа из переменных окружения (новая архитектура)
"""
import pytest
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from db import get_db
from db.models import AdminUser, AdminTronAddress, NodeSettings
from node import app
from settings import Settings
from services.admin import AdminService

# Тестовая БД
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Создает тестовую БД"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(AdminUser.__table__.create)
        await conn.run_sync(AdminTronAddress.__table__.create)
        await conn.run_sync(NodeSettings.__table__.create)
    
    TestSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with TestSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(AdminUser.__table__.drop)
        await conn.run_sync(AdminTronAddress.__table__.drop)
        await conn.run_sync(NodeSettings.__table__.drop)
    
    await engine.dispose()


@pytest.fixture
async def test_client(test_db):
    """Создает тестовый HTTP клиент"""
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


class TestEnvInit:
    """Тесты инициализации из ENV"""
    
    @pytest.mark.asyncio
    async def test_init_password_from_env(self, test_client, test_db, monkeypatch):
        """Инициализация password админа из ENV"""
        monkeypatch.setenv("ADMIN_METHOD", "password")
        monkeypatch.setenv("ADMIN_USERNAME", "env_admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "env_pass123")

        # Инициализируем через AdminService
        settings = Settings()
        await AdminService.init_from_env(settings.admin, test_db)

        # Проверяем
        response = await test_client.get("/api/admin/info")
        assert response.status_code == 200
        data = response.json()
        assert data["has_password"] is True
        assert data["username"] == "env_admin"

    @pytest.mark.asyncio
    async def test_init_tron_from_env(self, test_client, test_db, monkeypatch):
        """Инициализация TRON админа из ENV"""
        monkeypatch.setenv("ADMIN_METHOD", "tron")
        monkeypatch.setenv("ADMIN_TRON_ADDRESS", "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX")

        settings = Settings()
        await AdminService.init_from_env(settings.admin, test_db)

        response = await test_client.get("/api/admin/info")
        assert response.status_code == 200
        data = response.json()
        assert data["has_password"] is False
        assert data["tron_addresses_count"] == 1

    @pytest.mark.asyncio
    async def test_env_overrides_db(self, test_client, test_db, monkeypatch):
        """ENV переменные перезаписывают БД (ENV > БД)"""
        # Создаем админа через API
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "db_admin", "password": "db_pass123"}
        )
        
        # Проверяем что админ существует
        result = await test_db.execute(select(AdminUser))
        assert result.scalar_one_or_none() is not None

        # Инициализируем из ENV - должно перезаписать
        monkeypatch.setenv("ADMIN_METHOD", "password")
        monkeypatch.setenv("ADMIN_USERNAME", "env_override")
        monkeypatch.setenv("ADMIN_PASSWORD", "env_override_pass")

        settings = Settings()
        await AdminService.init_from_env(settings.admin, test_db)

        response = await test_client.get("/api/admin/info")
        assert response.status_code == 200
        assert response.json()["username"] == "env_override"

    @pytest.mark.asyncio
    async def test_no_init_if_not_configured(self, test_db, monkeypatch):
        """Не инициализируется если ENV неполные"""
        monkeypatch.setenv("ADMIN_METHOD", "password")
        monkeypatch.setenv("ADMIN_USERNAME", "incomplete")
        # ADMIN_PASSWORD отсутствует

        settings = Settings()
        result = await AdminService.init_from_env(settings.admin, test_db)

        assert result is False  # Не инициализировано

