"""
Лаконичные тесты инициализации администратора через env vars
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from db.models import AdminUser, NodeSettings
from settings import AdminSettings
from services.admin import AdminService

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


class TestAdminEnvInit:
    """Компактные тесты инициализации админа из env vars"""
    
    @pytest.mark.asyncio
    async def test_init_password_from_env(self, test_db):
        """Успешная инициализация password админа"""
        settings = AdminSettings(method="password", username="admin", password="pass12345")
        admin = await AdminService.init_from_env(settings, test_db)
        
        assert admin is not None
        assert admin.auth_method == "password"
        assert admin.username == "admin"
    
    @pytest.mark.asyncio
    async def test_init_tron_from_env(self, test_db):
        """Успешная инициализация TRON админа"""
        settings = AdminSettings(method="tron", tron_address="TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX")
        admin = await AdminService.init_from_env(settings, test_db)
        
        assert admin is not None
        assert admin.auth_method == "tron"
        assert admin.tron_address == "TYwXzKjQbQxnYbJUvCvyBpGpfhJhkDn1eX"
    
    @pytest.mark.asyncio
    async def test_override_existing_admin(self, test_db):
        """ENV VARS перезаписывают существующего админа"""
        await AdminService.create_password_admin("existing", "pass12345", test_db)
        
        settings = AdminSettings(method="password", username="newadmin", password="newpass123")
        admin = await AdminService.init_from_env(settings, test_db)
        
        assert admin is not None
        assert admin.username == "newadmin"
    
    @pytest.mark.asyncio
    async def test_no_init_if_not_configured(self, test_db):
        """Не инициализирует если env vars не настроены"""
        settings = AdminSettings()
        admin = await AdminService.init_from_env(settings, test_db)
        
        assert admin is None


class TestAdminSettingsValidation:
    """Компактные тесты валидации AdminSettings"""
    
    def test_is_configured_password(self):
        """is_configured работает для password"""
        assert AdminSettings(method="password", username="a", password="p").is_configured is True
        assert AdminSettings(method="password", username="a").is_configured is False
    
    def test_is_configured_tron(self):
        """is_configured работает для TRON"""
        assert AdminSettings(method="tron", tron_address="T123").is_configured is True
        assert AdminSettings(method="tron").is_configured is False

