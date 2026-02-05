# Protocol Tests

Тесты для реализаций протоколов Aries RFCs.

## Структура

- `test_trust_ping.py` - тесты для Trust Ping протокола (RFC 0048)

## Запуск тестов

### Все тесты протоколов

```bash
pytest tests/test_protocols/
```

### Только Trust Ping тесты

```bash
pytest tests/test_protocols/test_trust_ping.py
```

### Конкретный тест

```bash
pytest tests/test_protocols/test_trust_ping.py::TestTrustPingHandler::test_create_ping_message
```

### С подробным выводом

```bash
pytest tests/test_protocols/test_trust_ping.py -v
```

### С покрытием кода

```bash
pytest tests/test_protocols/ --cov=services.protocols --cov-report=html
```

## Требования

Установите зависимости для тестирования:

```bash
pip install pytest pytest-asyncio pytest-cov
```

## Структура тестов Trust Ping

### TestTrustPingHandler
- Тесты базовой функциональности handler'а
- Создание ping/pong сообщений
- Обработка входящих сообщений
- Валидация сообщений

### TestTrustPingEndToEnd
- End-to-end тесты с упаковкой/распаковкой
- Полный цикл ping-pong между двумя агентами
- Тесты с шифрованием и без

### TestTrustPingWithDifferentKeys
- Тесты с различными типами ключей:
  - Ethereum (secp256k1)
  - RSA
  - EC (различные кривые)

### TestTrustPingSchemas
- Валидация Pydantic схем
- Проверка структуры сообщений

## Примеры

### Простой запуск

```bash
# Все тесты
pytest

# Только async тесты
pytest -m asyncio

# Только unit тесты
pytest -m unit
```

### С фильтрацией

```bash
# Тесты, содержащие "ping" в названии
pytest -k ping

# Тесты класса TestTrustPingHandler
pytest tests/test_protocols/test_trust_ping.py::TestTrustPingHandler
```

## Добавление новых тестов

1. Создайте новый файл `test_<protocol_name>.py`
2. Используйте fixtures для setup/teardown
3. Именуйте тесты описательно: `test_<what_is_being_tested>`
4. Используйте `@pytest.mark.asyncio` для async тестов
5. Группируйте связанные тесты в классы

Пример:

```python
import pytest
from services.protocols.your_protocol import YourProtocolHandler

class TestYourProtocol:
    @pytest.fixture
    def handler(self):
        return YourProtocolHandler(...)
    
    @pytest.mark.asyncio
    async def test_something(self, handler):
        result = await handler.do_something()
        assert result is not None
```

