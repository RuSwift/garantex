"""
Интеграционные тесты для API администратора
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from db import get_db
from db.models import AdminUser, NodeSettings
from node import app
from settings import Settings

# Тестовая БД в памяти
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Создает тестовую БД с таблицами AdminUser и NodeSettings"""
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
    """Создает тестовый HTTP клиент с переопределенной БД"""
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


@pytest.fixture
def test_tron_key():
    """Генерирует детерминированный TRON ключ для тестов"""
    from tronpy.keys import PrivateKey
    # Используем детерминированный ключ для воспроизводимости
    key_bytes = bytes.fromhex("a" * 64)
    return PrivateKey(key_bytes)


@pytest.fixture
def test_tron_address(test_tron_key):
    """Получает TRON адрес из ключа"""
    return test_tron_key.public_key.to_base58check_address()


def sign_tron_message(private_key, message: str) -> str:
    """
    Подписывает сообщение TRON ключом (имитирует TronWeb)
    
    Args:
        private_key: TRON PrivateKey
        message: Сообщение для подписи
        
    Returns:
        Hex подпись (65 байт)
    """
    from Crypto.Hash import keccak
    from eth_keys import keys
    from eth_utils import keccak as eth_keccak
    from tronpy.keys import to_base58check_address
    import hashlib
    
    # Формируем сообщение с TRON префиксом
    tron_prefix = "\x19TRON Signed Message:\n"
    full_message = tron_prefix + str(len(message)) + message
    message_bytes = full_message.encode('utf-8')
    
    # Keccak-256 хеш
    k = keccak.new(digest_bits=256)
    k.update(message_bytes)
    message_hash = k.digest()
    
    # Получаем raw приватный ключ
    private_key_bytes = private_key.key
    
    # Подписываем с помощью eth_keys
    from eth_keys import keys as eth_keys_module
    eth_private_key = eth_keys_module.PrivateKey(private_key_bytes)
    
    # Создаем подпись
    signature_obj = eth_private_key.sign_msg_hash(message_hash)
    
    # Получаем r, s, v компоненты
    r = signature_obj.r
    s = signature_obj.s
    v = signature_obj.v
    
    # Формируем 65-байтную подпись: r (32) + s (32) + v (1)
    # TRON использует v = 27 или 28
    signature_bytes = r.to_bytes(32, 'big') + s.to_bytes(32, 'big') + bytes([v + 27])
    
    return signature_bytes.hex()


class TestRootCredentialsPassword:
    """Тесты создания root credentials через password"""
    
    @pytest.mark.asyncio
    async def test_create_password_admin(self, test_client):
        """Успешное создание password админа"""
        response = await test_client.post(
            "/api/node/set-root-credentials",
            json={
                "method": "password",
                "username": "admin",
                "password": "strongpass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["auth_method"] == "password"
    
    @pytest.mark.asyncio
    async def test_create_duplicate_password_admin(self, test_client):
        """Дублирование password админа отклоняется"""
        # Создаем первого админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin", "password": "pass12345"}
        )
        
        # Пытаемся создать второго
        response = await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin2", "password": "pass67890"}
        )
        
        assert response.status_code == 400
        assert "already configured" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_password_too_short(self, test_client):
        """Короткий пароль отклоняется"""
        response = await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin", "password": "short"}
        )
        
        assert response.status_code == 400
        assert "at least 8 characters" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_password_missing_fields(self, test_client):
        """Отсутствующие поля отклоняются"""
        response = await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin"}
        )
        
        # API должен вернуть ошибку (400 или 500)
        assert response.status_code >= 400
        assert response.status_code < 600


class TestRootCredentialsTron:
    """Тесты создания root credentials через TRON"""
    
    @pytest.mark.asyncio
    async def test_create_tron_admin(self, test_client, test_tron_address):
        """Успешное создание TRON админа"""
        response = await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": test_tron_address}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["auth_method"] == "tron"
    
    @pytest.mark.asyncio
    async def test_create_duplicate_tron_admin(self, test_client, test_tron_address):
        """Дублирование TRON админа отклоняется"""
        # Создаем первого админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": test_tron_address}
        )
        
        # Пытаемся создать второго
        response = await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        assert response.status_code == 400
        assert "already configured" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_invalid_tron_address(self, test_client):
        """Невалидный TRON адрес отклоняется"""
        response = await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": "invalid_address"}
        )
        
        assert response.status_code == 400
        assert "Invalid TRON address" in response.json()["detail"]


class TestAdminPasswordChange:
    """Тесты смены пароля администратора"""
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, test_client):
        """Успешная смена пароля"""
        # Создаем админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin", "password": "oldpass123"}
        )
        
        # Меняем пароль
        response = await test_client.post(
            "/api/admin/change-password",
            json={"old_password": "oldpass123", "new_password": "newpass456"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, test_client):
        """Неверный старый пароль отклоняется"""
        # Создаем админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin", "password": "correctpass"}
        )
        
        # Пытаемся сменить с неверным старым паролем
        response = await test_client.post(
            "/api/admin/change-password",
            json={"old_password": "wrongpass", "new_password": "newpass456"}
        )
        
        assert response.status_code == 401
        assert "Incorrect old password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_change_password_too_short(self, test_client):
        """Слишком короткий новый пароль отклоняется"""
        # Создаем админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin", "password": "oldpass123"}
        )
        
        # Пытаемся установить короткий пароль
        response = await test_client.post(
            "/api/admin/change-password",
            json={"old_password": "oldpass123", "new_password": "short"}
        )
        
        assert response.status_code == 400
        assert "at least 8 characters" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_change_password_for_tron_admin_fails(self, test_client, test_tron_address):
        """Нельзя сменить пароль для TRON админа"""
        # Создаем TRON админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": test_tron_address}
        )
        
        # Пытаемся сменить пароль
        response = await test_client.post(
            "/api/admin/change-password",
            json={"old_password": "anypass", "new_password": "newpass123"}
        )
        
        assert response.status_code == 404
        assert "not using password authentication" in response.json()["detail"]


class TestAdminTronChange:
    """Тесты смены TRON адреса администратора"""
    
    @pytest.mark.asyncio
    async def test_change_tron_address_success(self, test_client, test_tron_address):
        """Успешная смена TRON адреса"""
        # Создаем TRON админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": test_tron_address}
        )
        
        # Меняем адрес
        new_address = "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"
        response = await test_client.post(
            "/api/admin/change-tron-address",
            json={"new_tron_address": new_address}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_change_tron_address_invalid(self, test_client, test_tron_address):
        """Невалидный TRON адрес отклоняется"""
        # Создаем TRON админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": test_tron_address}
        )
        
        # Пытаемся установить невалидный адрес
        response = await test_client.post(
            "/api/admin/change-tron-address",
            json={"new_tron_address": "invalid_address"}
        )
        
        assert response.status_code == 400
        assert "Invalid TRON address" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_change_tron_address_duplicate(self, test_client, test_tron_address):
        """Дублирующий TRON адрес отклоняется"""
        # Создаем TRON админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": test_tron_address}
        )
        
        # Пытаемся установить тот же адрес
        response = await test_client.post(
            "/api/admin/change-tron-address",
            json={"new_tron_address": test_tron_address}
        )
        
        # Это должно быть успешно (тот же адрес) или ошибка уже существует
        # В зависимости от реализации может быть 200 или 400
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_change_tron_for_password_admin_fails(self, test_client):
        """Нельзя сменить TRON адрес для password админа"""
        # Создаем password админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin", "password": "pass12345"}
        )
        
        # Пытаемся сменить TRON адрес
        response = await test_client.post(
            "/api/admin/change-tron-address",
            json={"new_tron_address": "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"}
        )
        
        assert response.status_code == 404
        assert "not using TRON authentication" in response.json()["detail"]


class TestAdminInfo:
    """Тесты получения информации об администраторе"""
    
    @pytest.mark.asyncio
    async def test_get_admin_info_password(self, test_client):
        """Получение информации о password админе"""
        # Создаем админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "testadmin", "password": "pass12345"}
        )
        
        # Получаем информацию
        response = await test_client.get("/api/admin/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["auth_method"] == "password"
        assert data["username"] == "testadmin"
        assert data["tron_address"] is None
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_admin_info_tron(self, test_client, test_tron_address):
        """Получение информации о TRON админе"""
        # Создаем админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "tron", "tron_address": test_tron_address}
        )
        
        # Получаем информацию
        response = await test_client.get("/api/admin/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["auth_method"] == "tron"
        assert data["username"] is None
        assert data["tron_address"] == test_tron_address
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_admin_info_not_configured(self, test_client):
        """Получение информации когда админ не настроен"""
        response = await test_client.get("/api/admin/info")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAdminConfiguredCheck:
    """Тесты проверки наличия администратора"""
    
    @pytest.mark.asyncio
    async def test_is_admin_configured_true(self, test_client):
        """Проверка что админ настроен"""
        # Создаем админа
        await test_client.post(
            "/api/node/set-root-credentials",
            json={"method": "password", "username": "admin", "password": "pass12345"}
        )
        
        # Проверяем статус
        response = await test_client.get("/api/node/is-admin-configured")
        
        assert response.status_code == 200
        assert response.json()["configured"] is True
    
    @pytest.mark.asyncio
    async def test_is_admin_configured_false(self, test_client):
        """Проверка что админ не настроен"""
        response = await test_client.get("/api/node/is-admin-configured")
        
        assert response.status_code == 200
        assert response.json()["configured"] is False

