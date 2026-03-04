# Garantex API

FastAPI приложение

## Установка

1. Создайте виртуальное окружение:

```bash
python -m venv venv
```

1. Активируйте виртуальное окружение:

- Windows:

```bash
venv\Scripts\activate
```

- Linux/Mac:

```bash
source venv/bin/activate
```

1. Установите зависимости:

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

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Эндпоинты

### Базовые эндпоинты

- `GET /` - Корневой эндпоинт
- `GET /health` - Проверка здоровья приложения

### Web3 Авторизация

Приложение поддерживает авторизацию через Web3 кошельки:

- **MetaMask** (Ethereum)
- **TrustWallet** (Ethereum + TRON)
- **TronLink** (TRON)
- **WalletConnect** (Mobile)

#### Процесс авторизации

1. **Получение nonce** - `POST /auth/nonce`
  ```json
   {
     "wallet_address": "0x..."
   }
  ```
   Ответ:
2. **Подпись сообщения** - Пользователь подписывает полученное сообщение в своем кошельке
3. **Верификация подписи** - `POST /auth/verify`
  ```json
   {
     "wallet_address": "0x...",
     "signature": "0x..."
   }
  ```
   Ответ:
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

## TRON Авторизация

Приложение поддерживает авторизацию через TRON кошельки (TronLink, TrustWallet).

### Поддерживаемые браузеры

- ✅ **Google Chrome** (рекомендуется)
- ✅ **Brave Browser** (рекомендуется)
- ✅ **Microsoft Edge** (с дополнительной настройкой)
- ✅ **Firefox**
- ✅ **Safari**
- ✅ **Opera**

### Microsoft Edge - Быстрый старт

При использовании Microsoft Edge могут возникнуть проблемы с TronLink. Для решения:

1. **Установите TronLink:**
  - Откройте [Chrome Web Store](https://chrome.google.com/webstore/detail/tronlink/ibnejdfjmmkpcnlpebklmnkoeoihofec)
  - Установите расширение
  - **Или** скачайте с [официального сайта](https://www.tronlink.org/)
2. **Настройте кошелек:**
  - Разблокируйте TronLink (введите пароль)
  - Убедитесь, что сайт добавлен в Connected Sites
3. **Обновите страницу** (F5) и попробуйте авторизоваться

### Устранение проблем

Если авторизация в Edge не работает:

- 📖 **Полное руководство:** [TRONLINK_EDGE_TROUBLESHOOTING.md](./TRONLINK_EDGE_TROUBLESHOOTING.md)
- 🚀 **Быстрый старт:** [docs/EDGE_TRONLINK_QUICKSTART.md](./docs/EDGE_TRONLINK_QUICKSTART.md)

**Распространенные ошибки:**

- `Invalid transaction provided` - Разблокируйте кошелек и обновите страницу
- `Connection error` - Отключите другие Web3 расширения
- Кнопка не отображается - Проверьте консоль браузера (F12)

### Альтернативные методы

Если TronLink в Edge не работает:

1. Используйте **Chrome** или **Brave** (стабильнее)
2. Используйте **мобильное приложение** TronLink + WalletConnect

## Переменные окружения

Создайте файл `.env` для настройки:

```env
JWT_SECRET=your-secret-key-change-in-production
```

**Важно:** В продакшене обязательно используйте надежный секретный ключ для JWT!

1. Конфигурация Multisig кошельков
  1. TFV7pibMRjandNG6yGN94YwfyG3we2mWR6
  2. TGdsPzrjHzxNqBDMUCZ9z7H72PBgHb7YDL
2. Контракт
  1. TQ8YELnncArCgnfgGdkr1EWjhJuYTRALjY



