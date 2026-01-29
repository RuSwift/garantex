# Garantex API

FastAPI приложение

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
```

2. Активируйте виртуальное окружение:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

### Разработка
```bash
python main.py
```

Или с помощью uvicorn:
```bash
uvicorn main:app --reload
```

### Продакшн
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Документация

После запуска приложения документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Эндпоинты

### Базовые эндпоинты

- `GET /` - Корневой эндпоинт
- `GET /health` - Проверка здоровья приложения

### Web3 Авторизация

Приложение поддерживает авторизацию через Web3 кошельки:
- **MetaMask**
- **TrustWallet**
- **WalletConnect**

#### Процесс авторизации

1. **Получение nonce** - `POST /auth/nonce`
   ```json
   {
     "wallet_address": "0x..."
   }
   ```
   Ответ:
   ```json
   {
     "nonce": "abc123...",
     "message": "Please sign this message to authenticate:\n\nNonce: abc123..."
   }
   ```

2. **Подпись сообщения** - Пользователь подписывает полученное сообщение в своем кошельке

3. **Верификация подписи** - `POST /auth/verify`
   ```json
   {
     "wallet_address": "0x...",
     "signature": "0x..."
   }
   ```
   Ответ:
   ```json
   {
     "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "wallet_address": "0x..."
   }
   ```

4. **Использование токена** - Добавьте токен в заголовок `Authorization: Bearer <token>` для доступа к защищенным эндпоинтам

#### Защищенные эндпоинты

- `GET /auth/me` - Получить информацию о текущем пользователе
  - Требует: `Authorization: Bearer <token>`
  - Ответ:
    ```json
    {
      "wallet_address": "0x..."
    }
    ```

## Переменные окружения

Создайте файл `.env` для настройки:

```env
JWT_SECRET=your-secret-key-change-in-production
```

**Важно:** В продакшене обязательно используйте надежный секретный ключ для JWT!
