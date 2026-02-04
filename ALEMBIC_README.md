# Alembic Migrations

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Настройка .env файла


Отредактируйте `.env` файл с вашими настройками PostgreSQL и Redis.

## Запуск миграций

### Применить все миграции

```bash
alembic upgrade head
```

### Откатить последнюю миграцию

```bash
alembic downgrade -1
```

### Создать новую миграцию

```bash
alembic revision --autogenerate -m "Описание изменений"
```

### Просмотр текущей версии

```bash
alembic current
```

### Просмотр истории миграций

```bash
alembic history
```

## Структура базы данных

### Таблица `node_settings`

Хранит зашифрованные данные для настройки ноды:

- `id` - Primary key
- `encrypted_mnemonic` - Зашифрованная мнемоническая фраза (опционально)
- `encrypted_pem` - Зашифрованные данные PEM ключа (опционально)
- `key_type` - Тип ключа: 'mnemonic' или 'pem'
- `ethereum_address` - Ethereum адрес, полученный из ключа (уникальный индекс)
- `is_active` - Активен ли этот ключ
- `created_at` - Дата создания
- `updated_at` - Дата последнего обновления

## Использование в коде

```python
from db import init_db, get_db
from db.models import NodeSettings
from settings import Settings

# Инициализация БД
settings = Settings()
engine = init_db(settings.database)

# Использование в зависимости
from fastapi import Depends
from db import get_db

@app.get("/example")
async def example(db: AsyncSession = Depends(get_db)):
    # Работа с БД
    result = await db.query(NodeSettings).first()
    return result
```

