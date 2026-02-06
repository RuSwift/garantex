"""
Тесты для новой архитектуры админа: один админ + множество TRON адресов
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from db import get_db
from db.models import AdminUser, AdminTronAddress, NodeSettings
from node import app
from settings import Settings

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


class TestPasswordManagement:
    """Тесты управления паролем"""
    
    @pytest.mark.asyncio
    async def test_set_password(self, test_client):
        """Установка пароля"""
        response = await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_change_password(self, test_client):
        """Смена пароля"""
        # Установим пароль
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "oldpass123"}
        )
        
        # Сменим
        response = await test_client.post(
            "/api/admin/change-password",
            json={"old_password": "oldpass123", "new_password": "newpass123"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_remove_password_without_tron_fails(self, test_client):
        """Нельзя удалить пароль если нет TRON адресов"""
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        response = await test_client.delete("/api/admin/password")
        
        assert response.status_code == 400
        assert "no TRON addresses" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_remove_password_with_tron_succeeds(self, test_client):
        """Можно удалить пароль если есть TRON адреса"""
        # Установим пароль
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        # Добавим TRON адрес
        await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX", "label": "Main"}
        )
        
        # Удалим пароль
        response = await test_client.delete("/api/admin/password")
        
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestTronAddresses:
    """Тесты управления TRON адресами"""
    
    @pytest.mark.asyncio
    async def test_add_tron_address(self, test_client):
        """Добавление TRON адреса"""
        response = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX", "label": "Main wallet"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_add_multiple_tron_addresses(self, test_client):
        """Добавление нескольких TRON адресов"""
        r1 = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        r2 = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"}
        )
        
        assert r1.status_code == 200
        assert r2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_tron_addresses(self, test_client):
        """Получение списка TRON адресов"""
        await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX", "label": "Test"}
        )
        
        response = await test_client.get("/api/admin/tron-addresses")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["addresses"]) == 1
        assert data["addresses"][0]["label"] == "Test"
    
    @pytest.mark.asyncio
    async def test_update_tron_address(self, test_client):
        """Обновление TRON адреса"""
        await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        list_resp = await test_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await test_client.put(
            f"/api/admin/tron-addresses/{tron_id}",
            json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_toggle_tron_address(self, test_client):
        """Toggle TRON адреса"""
        await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        list_resp = await test_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await test_client.patch(
            f"/api/admin/tron-addresses/{tron_id}/toggle",
            json={"is_active": False}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_tron_address(self, test_client):
        """Удаление TRON адреса"""
        # Сначала добавим пароль (чтобы не удалить последний способ авторизации)
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        # Добавим TRON адрес
        await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        list_resp = await test_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await test_client.delete(f"/api/admin/tron-addresses/{tron_id}")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_cannot_delete_last_auth_method(self, test_client):
        """Нельзя удалить последний способ авторизации"""
        await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        list_resp = await test_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await test_client.delete(f"/api/admin/tron-addresses/{tron_id}")
        
        assert response.status_code == 400
        assert "last authentication method" in response.json()["detail"]


class TestAdminInfo:
    """Тесты получения информации об админе"""
    
    @pytest.mark.asyncio
    async def test_get_admin_info(self, test_client, test_db):
        """Получение информации об админе"""
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        response = await test_client.get("/api/admin/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["has_password"] is True
        assert data["username"] == "admin"
        assert data["tron_addresses_count"] == 0
    
    @pytest.mark.asyncio
    async def test_is_admin_configured(self, test_client):
        """Проверка конфигурации админа"""
        # Не настроен
        r1 = await test_client.get("/api/node/is-admin-configured")
        assert r1.json()["configured"] is False
        
        # Настроим пароль
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        r2 = await test_client.get("/api/node/is-admin-configured")
        assert r2.json()["configured"] is True
        assert r2.json()["has_password"] is True

