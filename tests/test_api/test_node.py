"""
Тесты для API инициализации ноды
Использует PostgreSQL из docker-compose через централизованные фикстуры conftest.py
"""
import pytest
from sqlalchemy import select
from db.models import NodeSettings
from didcomm.crypto import EthCrypto

# Фикстуры test_db, test_client, valid_mnemonic, test_secret, set_test_secret 
# импортируются из tests/conftest.py


class TestNodeInitialization:
    """Тесты инициализации ноды"""
    
    @pytest.mark.asyncio
    async def test_init_node_with_valid_mnemonic(self, admin_client, valid_mnemonic, set_test_secret):
        """Тест успешной инициализации ноды с мнемонической фразой"""
        response = await admin_client.post(
            "/api/node/init",
            json={"mnemonic": valid_mnemonic}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "Node initialized successfully"
        assert "did" in data
        assert data["did"].startswith("did:peer:1:z")
        assert "address" in data
        assert data["address"].startswith("0x")
        assert data["key_type"] == "mnemonic"
        assert "public_key" in data
        assert "did_document" in data
    
    @pytest.mark.asyncio
    async def test_init_node_with_invalid_mnemonic(self, admin_client, set_test_secret):
        """Тест инициализации с невалидной мнемонической фразой"""
        response = await admin_client.post(
            "/api/node/init",
            json={"mnemonic": "invalid mnemonic phrase that does not work"}
        )
        
        assert response.status_code == 400
        assert "Invalid mnemonic" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_init_node_twice_returns_error(self, admin_client, valid_mnemonic, set_test_secret):
        """Тест повторной инициализации ноды - должна вернуть 400 ошибку"""
        # Первая инициализация
        response1 = await admin_client.post(
            "/api/node/init",
            json={"mnemonic": valid_mnemonic}
        )
        assert response1.status_code == 200
        
        # Вторая инициализация с другой мнемонической фразой
        from mnemonic import Mnemonic
        mnemo = Mnemonic("english")
        another_mnemonic = mnemo.generate(strength=128)
        
        response2 = await admin_client.post(
            "/api/node/init",
            json={"mnemonic": another_mnemonic}
        )
        
        assert response2.status_code == 400
        assert "Нода инициализируется только один раз" in response2.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_init_node_pem_with_valid_key(self, admin_client, set_test_secret):
        """Тест успешной инициализации ноды с PEM ключом"""
        from didcomm.crypto import KeyPair
        
        # Генерируем RSA ключ
        keypair = KeyPair.generate_rsa(key_size=2048)
        pem_data = keypair.to_pem().decode('utf-8')
        
        response = await admin_client.post(
            "/api/node/init-pem",
            json={"pem_data": pem_data, "password": None}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "Node initialized successfully"
        assert "did" in data
        assert data["did"].startswith("did:peer:1:z")
        assert data["key_type"] == "pem"
        assert "public_key" in data
        assert "did_document" in data
    
    @pytest.mark.asyncio
    async def test_init_node_pem_twice_returns_error(self, admin_client, set_test_secret):
        """Тест повторной инициализации ноды через PEM - должна вернуть 400 ошибку"""
        from didcomm.crypto import KeyPair
        
        # Первая инициализация
        keypair1 = KeyPair.generate_rsa(key_size=2048)
        pem_data1 = keypair1.to_pem().decode('utf-8')
        
        response1 = await admin_client.post(
            "/api/node/init-pem",
            json={"pem_data": pem_data1, "password": None}
        )
        assert response1.status_code == 200
        
        # Вторая инициализация с другим ключом
        keypair2 = KeyPair.generate_rsa(key_size=2048)
        pem_data2 = keypair2.to_pem().decode('utf-8')
        
        response2 = await admin_client.post(
            "/api/node/init-pem",
            json={"pem_data": pem_data2, "password": None}
        )
        
        assert response2.status_code == 400
        assert "Нода инициализируется только один раз" in response2.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_init_node_pem_with_public_key_fails(self, admin_client, set_test_secret):
        """Тест что инициализация с публичным ключом вместо приватного возвращает ошибку"""
        # Публичный ключ в PEM формате (это должно быть отклонено)
        public_key_pem = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE7Z9xKVmXPJvXVJqPvXzPvXzPvXzP
vXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvQ==
-----END PUBLIC KEY-----"""
        
        response = await admin_client.post(
            "/api/node/init-pem",
            json={"pem_data": public_key_pem, "password": None}
        )
        
        assert response.status_code == 400
        assert "PRIVATE KEY" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_init_node_pem_with_certificate_fails(self, admin_client, set_test_secret):
        """Тест что инициализация с сертификатом вместо ключа возвращает ошибку"""
        # Сертификат в PEM формате (это должно быть отклонено)
        certificate_pem = """-----BEGIN CERTIFICATE-----
MIICljCCAX4CCQCKz8pZvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzP
vXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzPvXzP
-----END CERTIFICATE-----"""
        
        response = await admin_client.post(
            "/api/node/init-pem",
            json={"pem_data": certificate_pem, "password": None}
        )
        
        assert response.status_code == 400
        assert "PRIVATE KEY" in response.json()["detail"]


class TestNodeKeyInfo:
    """Тесты получения информации о ключе ноды"""
    
    @pytest.mark.asyncio
    async def test_get_key_info_when_initialized(self, admin_client, valid_mnemonic, set_test_secret):
        """Тест получения информации о ключе после инициализации"""
        # Инициализируем ноду
        await admin_client.post(
            "/api/node/init",
            json={"mnemonic": valid_mnemonic}
        )
        
        # Получаем информацию о ключе
        response = await admin_client.get("/api/node/key-info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "address" in data
        assert "key_type" in data
        assert "public_key" in data
        assert "did" in data
        assert "did_document" in data
    
    @pytest.mark.asyncio
    async def test_get_key_info_when_not_initialized(self, admin_client, set_test_secret):
        """Тест получения информации о ключе до инициализации"""
        response = await admin_client.get("/api/node/key-info")
        
        assert response.status_code == 404
        assert "не инициализирована" in response.json()["detail"]


class TestEnvVarsBehavior:
    """Тесты поведения с env vars"""
    
    @pytest.mark.asyncio
    async def test_env_vars_take_priority_over_db(self, admin_client, test_db, valid_mnemonic, set_test_secret, monkeypatch):
        """Тест что env vars имеют приоритет над БД"""
        # Инициализируем через API с одной мнемонической фразой
        await admin_client.post(
            "/api/node/init",
            json={"mnemonic": valid_mnemonic}
        )
        
        # Устанавливаем другую мнемоническую фразу в env vars
        env_mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        monkeypatch.setenv("MNEMONIC_PHRASE", env_mnemonic)
        
        # Получаем ключ - должен быть из env vars, не из БД
        response = await admin_client.get("/api/node/key-info")
        assert response.status_code == 200
        
        # Проверяем что адрес соответствует env_mnemonic, а не valid_mnemonic
        from didcomm.crypto import EthKeyPair
        expected_address = EthKeyPair.from_mnemonic(env_mnemonic).address
        db_address = EthKeyPair.from_mnemonic(valid_mnemonic).address
        
        actual_address = response.json()["address"]
        assert actual_address == expected_address
        assert actual_address != db_address
    
    @pytest.mark.asyncio
    async def test_db_not_overwritten_when_env_vars_used(self, admin_client, test_db, valid_mnemonic, set_test_secret, monkeypatch):
        """Тест что БД не перезатирается при наличии env vars"""
        # Инициализируем через API
        await admin_client.post(
            "/api/node/init",
            json={"mnemonic": valid_mnemonic}
        )
        
        # Запоминаем данные из БД
        result = await test_db.execute(select(NodeSettings))
        settings_before = result.scalar_one()
        encrypted_mnemonic_before = settings_before.encrypted_mnemonic
        
        # Устанавливаем другую мнемоническую фразу в env vars
        env_mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        monkeypatch.setenv("MNEMONIC_PHRASE", env_mnemonic)
        
        # Получаем ключ - должен использоваться env var
        response = await admin_client.get("/api/node/key-info")
        assert response.status_code == 200
        
        # Проверяем что данные в БД НЕ изменились
        result = await test_db.execute(select(NodeSettings))
        settings_after = result.scalar_one()
        
        assert settings_after.encrypted_mnemonic == encrypted_mnemonic_before
        assert settings_after.key_type == "mnemonic"
        assert settings_after.is_active is True
        
        # Проверяем что в БД все еще одна запись
        result = await test_db.execute(select(NodeSettings))
        all_settings = result.scalars().all()
        assert len(all_settings) == 1
    
    @pytest.mark.asyncio
    async def test_fallback_to_db_when_env_vars_empty(self, admin_client, test_db, valid_mnemonic, set_test_secret, monkeypatch):
        """Тест fallback на БД когда env vars не установлены"""
        # Убеждаемся что env vars для ключей НЕ установлены
        monkeypatch.delenv("MNEMONIC_PHRASE", raising=False)
        monkeypatch.delenv("MNEMONIC_ENCRYPTED_PHRASE", raising=False)
        monkeypatch.delenv("PEM", raising=False)
        
        # Инициализируем через API
        init_response = await admin_client.post(
            "/api/node/init",
            json={"mnemonic": valid_mnemonic}
        )
        assert init_response.status_code == 200
        init_address = init_response.json()["address"]
        
        # Env vars не установлены, получаем ключ - должен использоваться БД
        response = await admin_client.get("/api/node/key-info")
        assert response.status_code == 200
        
        actual_address = response.json()["address"]
        
        # Адрес должен совпадать с тем, что вернула инициализация
        assert actual_address == init_address
        
        # И должен совпадать с ожидаемым адресом из мнемоники
        from didcomm.crypto import EthKeyPair
        expected_address = EthKeyPair.from_mnemonic(valid_mnemonic).address
        assert actual_address == expected_address


class TestDatabaseEncryption:
    """Тесты шифрования данных в БД"""
    
    @pytest.mark.asyncio
    async def test_mnemonic_stored_encrypted(self, admin_client, test_db, valid_mnemonic, set_test_secret):
        """Тест что мнемоническая фраза хранится зашифрованной"""
        # Инициализируем ноду
        await admin_client.post(
            "/api/node/init",
            json={"mnemonic": valid_mnemonic}
        )
        
        # Проверяем что в БД данные зашифрованы
        result = await test_db.execute(select(NodeSettings))
        node_settings = result.scalar_one()
        
        assert node_settings.encrypted_mnemonic is not None
        # Зашифрованные данные не должны содержать исходную фразу
        assert valid_mnemonic not in node_settings.encrypted_mnemonic
        # Должны быть в формате base64
        import base64
        try:
            base64.b64decode(node_settings.encrypted_mnemonic)
        except Exception:
            pytest.fail("Encrypted data is not valid base64")
    
    @pytest.mark.asyncio
    async def test_pem_stored_encrypted(self, admin_client, test_db, set_test_secret):
        """Тест что PEM данные хранятся зашифрованными"""
        from didcomm.crypto import KeyPair
        
        keypair = KeyPair.generate_rsa(key_size=2048)
        pem_data = keypair.to_pem().decode('utf-8')
        
        # Инициализируем ноду
        await admin_client.post(
            "/api/node/init-pem",
            json={"pem_data": pem_data, "password": None}
        )
        
        # Проверяем что в БД данные зашифрованы
        result = await test_db.execute(select(NodeSettings))
        node_settings = result.scalar_one()
        
        assert node_settings.encrypted_pem is not None
        # Зашифрованные данные не должны содержать исходные PEM данные
        assert "BEGIN" not in node_settings.encrypted_pem
        assert "PRIVATE KEY" not in node_settings.encrypted_pem
        # Должны быть в формате base64
        import base64
        try:
            base64.b64decode(node_settings.encrypted_pem)
        except Exception:
            pytest.fail("Encrypted data is not valid base64")

