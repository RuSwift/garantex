"""
Конфигурация для тестов протоколов DIDComm
Эти тесты используют in-memory моки вместо реальной БД
"""
import pytest
from unittest.mock import Mock
import db

# Эти тесты не требуют реальной БД, используют моки
# Но мы можем добавить поддержку PostgreSQL если потребуется в будущем

@pytest.fixture(scope="session", autouse=True)
def mock_db_session_local():
    """Mock SessionLocal для всех тестов протоколов"""
    original_session_local = db.SessionLocal
    db.SessionLocal = Mock()
    yield
    db.SessionLocal = original_session_local

