"""
Тесты инициализации админа из переменных окружения (новая архитектура)
Использует PostgreSQL из docker-compose через централизованные фикстуры conftest.py
"""
import pytest
from sqlalchemy import select
from db.models import AdminUser, AdminTronAddress, NodeSettings
from settings import Settings
from services.admin import AdminService

# Фикстуры test_db и test_client импортируются из tests/conftest.py


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

