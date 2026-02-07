"""
Тесты для новой архитектуры админа: один админ + множество TRON адресов
Использует PostgreSQL из docker-compose через централизованные фикстуры conftest.py
"""
import pytest
from sqlalchemy import select
from db.models import AdminUser, AdminTronAddress, NodeSettings

# Фикстуры test_db и test_client импортируются из tests/conftest.py


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
    async def test_change_password(self, test_client, admin_client):
        """Смена пароля"""
        # Установим пароль (первичная настройка, без авторизации)
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "oldpass123"}
        )
        
        # Сменим (требуется авторизация)
        response = await admin_client.post(
            "/api/admin/change-password",
            json={"old_password": "oldpass123", "new_password": "newpass123"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_remove_password_without_tron_fails(self, test_client, admin_client):
        """Нельзя удалить пароль если нет TRON адресов"""
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        response = await admin_client.delete("/api/admin/password")
        
        assert response.status_code == 400
        assert "no TRON addresses" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_remove_password_with_tron_succeeds(self, test_client, admin_client):
        """Можно удалить пароль если есть TRON адреса"""
        # Установим пароль (первичная настройка)
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        # Добавим TRON адрес (требуется авторизация)
        await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX", "label": "Main"}
        )
        
        # Удалим пароль (требуется авторизация)
        response = await admin_client.delete("/api/admin/password")
        
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestTronAddresses:
    """Тесты управления TRON адресами"""
    
    @pytest.mark.asyncio
    async def test_add_tron_address(self, admin_client):
        """Добавление TRON адреса"""
        response = await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX", "label": "Main wallet"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_add_multiple_tron_addresses(self, admin_client):
        """Добавление нескольких TRON адресов"""
        r1 = await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        r2 = await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"}
        )
        
        assert r1.status_code == 200
        assert r2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_tron_addresses(self, admin_client):
        """Получение списка TRON адресов"""
        await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX", "label": "Test"}
        )
        
        response = await admin_client.get("/api/admin/tron-addresses")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["addresses"]) == 1
        assert data["addresses"][0]["label"] == "Test"
    
    @pytest.mark.asyncio
    async def test_update_tron_address(self, admin_client):
        """Обновление TRON адреса"""
        await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        list_resp = await admin_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await admin_client.put(
            f"/api/admin/tron-addresses/{tron_id}",
            json={"tron_address": "THPvaUhoh2Qn2y9THCZML3H815hhFhn5YC"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_toggle_tron_address(self, admin_client):
        """Toggle TRON адреса"""
        await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        list_resp = await admin_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await admin_client.patch(
            f"/api/admin/tron-addresses/{tron_id}/toggle",
            json={"is_active": False}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_tron_address(self, test_client, admin_client):
        """Удаление TRON адреса"""
        # Сначала добавим пароль (чтобы не удалить последний способ авторизации)
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        # Добавим TRON адрес
        await admin_client.post(
            "/api/admin/tron-addresses",
            json={"tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        list_resp = await admin_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await admin_client.delete(f"/api/admin/tron-addresses/{tron_id}")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_cannot_delete_last_auth_method(self, test_client, test_db, test_secret):
        """Нельзя удалить последний способ авторизации"""
        import jwt
        from datetime import datetime, timedelta
        from services.admin import AdminService
        
        # Создаем админа ТОЛЬКО с TRON адресом (без пароля)
        await AdminService.add_tron_address("TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX", test_db)
        
        # Создаем токен с TRON авторизацией
        payload = {
            "admin": True,
            "tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX",
            "blockchain": "tron",
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, test_secret, algorithm="HS256")
        test_client.cookies.set("admin_token", token)
        
        list_resp = await test_client.get("/api/admin/tron-addresses")
        tron_id = list_resp.json()["addresses"][0]["id"]
        
        response = await test_client.delete(f"/api/admin/tron-addresses/{tron_id}")
        
        assert response.status_code == 400
        assert "last authentication method" in response.json()["detail"]


class TestAdminInfo:
    """Тесты получения информации об админе"""
    
    @pytest.mark.asyncio
    async def test_get_admin_info(self, test_client, admin_client, test_db):
        """Получение информации об админе"""
        await test_client.post(
            "/api/admin/set-password",
            json={"username": "admin", "password": "password123"}
        )
        
        response = await admin_client.get("/api/admin/info")
        
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

