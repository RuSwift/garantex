"""
Тесты управления списком TRON адресов администратора
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from db import get_db
from db.models import AdminUser, NodeSettings
from node import app
from settings import Settings

# Тестовая БД в памяти
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Создает тестовую БД"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(AdminUser.__table__.create)
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


class TestTronAddressesList:
    """Тесты получения списка TRON адресов"""
    
    @pytest.mark.asyncio
    async def test_get_empty_list(self, test_client):
        """Получение пустого списка"""
        response = await test_client.get("/api/admin/tron-addresses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["addresses"] == []
    
    @pytest.mark.asyncio
    async def test_get_list_with_addresses(self, test_client):
        """Получение списка с адресами"""
        # Добавляем TRON адреса (используем валидные тестовые адреса)
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"})
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"})
        
        response = await test_client.get("/api/admin/tron-addresses")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["addresses"]) == 2


class TestAddTronAddress:
    """Тесты добавления TRON адреса"""
    
    @pytest.mark.asyncio
    async def test_add_tron_address_success(self, test_client):
        """Успешное добавление TRON адреса"""
        response = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_add_multiple_tron_addresses(self, test_client):
        """Добавление нескольких TRON адресов"""
        response1 = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        response2 = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_add_duplicate_tron_address(self, test_client):
        """Дублирующий TRON адрес отклоняется"""
        address = "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"
        
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": address})
        
        response = await test_client.post("/api/admin/tron-addresses", json={"tron_address": address})
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_add_invalid_tron_address(self, test_client):
        """Невалидный TRON адрес отклоняется"""
        response = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "invalid_address"}
        )
        
        assert response.status_code == 400
        assert "Invalid TRON address" in response.json()["detail"]


class TestUpdateTronAddress:
    """Тесты изменения TRON адреса"""
    
    @pytest.mark.asyncio
    async def test_update_tron_address_success(self, test_client):
        """Успешное изменение TRON адреса"""
        # Добавляем адрес
        add_response = await test_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        # Получаем ID
        list_response = await test_client.get("/api/admin/tron-addresses")
        admin_id = list_response.json()["addresses"][0]["id"]
        
        # Изменяем адрес
        response = await test_client.put(
            f"/api/admin/tron-addresses/{admin_id}",
            json={"new_tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_update_to_duplicate_address(self, test_client):
        """Изменение на существующий адрес отклоняется"""
        # Добавляем два адреса
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"})
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"})
        
        # Получаем ID первого
        list_response = await test_client.get("/api/admin/tron-addresses")
        first_id = list_response.json()["addresses"][0]["id"]
        second_address = list_response.json()["addresses"][1]["tron_address"]
        
        # Пытаемся изменить первый на адрес второго
        response = await test_client.put(
            f"/api/admin/tron-addresses/{first_id}",
            json={"new_tron_address": second_address}
        )
        
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]


class TestDeleteTronAddress:
    """Тесты удаления TRON адреса"""
    
    @pytest.mark.asyncio
    async def test_delete_tron_address_success(self, test_client):
        """Успешное удаление TRON адреса"""
        # Добавляем два адреса
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"})
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"})
        
        # Получаем ID первого
        list_response = await test_client.get("/api/admin/tron-addresses")
        admin_id = list_response.json()["addresses"][0]["id"]
        
        # Удаляем
        response = await test_client.delete(f"/api/admin/tron-addresses/{admin_id}")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_cannot_delete_last_admin(self, test_client):
        """Нельзя удалить последнего админа"""
        # Добавляем один адрес
        await test_client.post("/api/admin/tron-addresses", json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"})
        
        # Получаем ID
        list_response = await test_client.get("/api/admin/tron-addresses")
        admin_id = list_response.json()["addresses"][0]["id"]
        
        # Пытаемся удалить последнего админа
        response = await test_client.delete(f"/api/admin/tron-addresses/{admin_id}")
        
        assert response.status_code == 400
        assert "last admin" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_non_existing_address(self, test_client):
        """Удаление несуществующего адреса"""
        response = await test_client.delete("/api/admin/tron-addresses/999")
        
        assert response.status_code == 404

