# TRON Multisig Service

Криптографический сервис для создания и управления мультиподписными кошельками в сети TRON. Поддерживает стандартную N/M мультиподпись, взвешенную мультиподпись и интеграцию с Web кошельками (TronLink).

## 📦 Содержание

- [Быстрый старт](#-быстрый-старт)
- [Основные возможности](#-основные-возможности)
- [Установка](#-установка)
- [Основные классы](#-основные-классы)
- [Примеры использования](#-примеры-использования)
- [Интеграция с Web кошельками](#-интеграция-с-web-кошельками)
- [Структура данных](#-структура-данных)
- [Безопасность](#-безопасность)
- [Тестирование](#-тестирование)

---

## ⚡ Быстрый старт

```python
from services.tron import TronMultisig

# 1. Создать сервис
multisig = TronMultisig()

# 2. Настроить 2/3 мультиподпись
config = multisig.create_multisig_config(
    required_signatures=2,
    owner_addresses=["TAddr1", "TAddr2", "TAddr3"]
)

# 3. Подготовить транзакцию
tx = multisig.prepare_transaction_for_signing(
    raw_data_hex="...",
    tx_id="...",
    config=config
)

# 4. Подписать (2 способа):

# Способ А: Локальный приватный ключ
tx = multisig.sign_transaction(tx, private_key, address)

# Способ Б: Web кошелек (TronLink) ⭐
tx = multisig.add_external_signature(tx, signature_from_web, address)

# 5. Отправить
if tx.is_ready_to_broadcast:
    signed_tx = multisig.combine_signatures(tx)
    # Broadcast to TRON network
```

---

## 🎯 Основные возможности

| Функция | Описание |
|---------|----------|
| **N/M мультиподпись** | Стандартная схема: нужно N подписей из M владельцев |
| **Взвешенная мультиподпись** | Каждому владельцу присваивается вес |
| **Web интеграция** | Работа с TronLink и другими web кошельками |
| **Верификация** | Проверка подписей ECDSA |
| **Утилиты** | Конвертация адресов, вычисление TX ID |

### N/M Мультиподпись
- **N** - минимальное количество подписей, необходимых для выполнения транзакции
- **M** - общее количество владельцев кошелька
- Условие: `1 <= N <= M`

### Взвешенная мультиподпись
В TRON можно настроить веса для каждого владельца:
- Каждому владельцу присваивается вес (например, 1, 2, 3)
- Устанавливается пороговый вес (threshold)
- Транзакция выполняется, когда сумма весов подписавших >= порога

---

## 📦 Установка

Все зависимости уже добавлены в корневой `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Зависимости для TRON Multisig:
- **ecdsa** (>=0.18.0) - ECDSA подписи для TRON
- **base58** (>=2.1.1) - Base58 кодирование для TRON адресов
- **pycryptodome** (>=3.19.0) - SHA3/Keccak256 для генерации адресов

### Проверка установки

```python
from services.tron import TronMultisig

multisig = TronMultisig()
config = multisig.create_multisig_config(
    required_signatures=2,
    owner_addresses=["TAddr1", "TAddr2", "TAddr3"]
)
print(f"✓ Конфигурация {config.required_signatures}/{config.total_owners} создана!")
```

---

## 🔑 Основные классы

### TronMultisig
Главный класс для работы с мультиподписью.

**Основные методы:**
- `create_multisig_config()` - создать конфигурацию N/M
- `prepare_transaction_for_signing()` - подготовить транзакцию
- `sign_transaction()` - подписать приватным ключом
- `add_external_signature()` - добавить подпись от web кошелька ⭐
- `verify_signature()` - проверить подпись
- `combine_signatures()` - объединить подписи для broadcast

**Утилиты:**
- `address_from_pubkey()` - конвертация публичного ключа в адрес
- `address_to_hex()` - конвертация base58 в hex
- `hex_to_address()` - конвертация hex в base58
- `calculate_tx_id()` - вычисление Transaction ID

### MultisigConfig
Конфигурация мультиподписи с валидацией.

**Поля:**
- `required_signatures` (N) - минимум подписей
- `total_owners` (M) - всего владельцев
- `owner_addresses` - адреса владельцев
- `owner_pubkeys` - публичные ключи (опционально)
- `threshold_weight` - пороговый вес (опционально)
- `owner_weights` - веса владельцев (опционально)

### MultisigTransaction
Транзакция с подписями.

**Свойства:**
- `signatures_count` - количество валидных подписей
- `total_weight` - суммарный вес подписей
- `is_ready_to_broadcast` - готова ли к отправке

---

## 💡 Примеры использования

### 1. Создание стандартной 2/3 мультиподписи

```python
from services.tron import TronMultisig

# Инициализация
multisig = TronMultisig()

# Адреса владельцев (base58 формат TRON)
owner_addresses = [
    "TYs7MvyFe1234567890abcdefghijklmno",  # Владелец 1
    "TXa8BcvFe1234567890abcdefghijklmno",  # Владелец 2
    "TZd9DezFe1234567890abcdefghijklmno",  # Владелец 3
]

# Создание конфигурации 2/3 (нужно 2 подписи из 3)
config = multisig.create_multisig_config(
    required_signatures=2,  # N
    owner_addresses=owner_addresses
)

print(f"Мультиподпись {config.required_signatures}/{config.total_owners} создана")
```

### 2. Создание взвешенной мультиподписи

```python
multisig = TronMultisig()

# Адреса и веса владельцев
owner_addresses = [
    "TYs7MvyFe1234567890abcdefghijklmno",  # CEO: вес 3
    "TXa8BcvFe1234567890abcdefghijklmno",  # CTO: вес 2
    "TZd9DezFe1234567890abcdefghijklmno",  # Dev: вес 1
]

owner_weights = [3, 2, 1]
threshold_weight = 4  # Пороговый вес

# Возможные комбинации:
# - CEO (3) + CTO (2) = 5 >= 4 ✓
# - CEO (3) + Dev (1) = 4 >= 4 ✓
# - CTO (2) + Dev (1) = 3 < 4 ✗

config = multisig.create_multisig_config(
    required_signatures=2,  # Минимум 2 подписи
    owner_addresses=owner_addresses,
    threshold_weight=threshold_weight,
    owner_weights=owner_weights
)

print(f"Взвешенная мультиподпись с порогом {threshold_weight} создана")
```

### 3. Подпись транзакции приватным ключом

```python
multisig = TronMultisig()

# Получены от TRON API (например, через tronweb.transactionBuilder.sendTrx())
raw_data_hex = "0a029a6122..."
tx_id = "abc123def456..."

# Подготовка транзакции
transaction = multisig.prepare_transaction_for_signing(
    raw_data_hex=raw_data_hex,
    tx_id=tx_id,
    config=config,
    contract_type="TransferContract"
)

# Подпись первым владельцем
private_key_1 = "your_private_key_hex_64_chars"
owner_address_1 = "TYs7MvyFe1234567890abcdefghijklmno"

transaction = multisig.sign_transaction(
    transaction=transaction,
    private_key_hex=private_key_1,
    signer_address=owner_address_1
)

print(f"Подписей: {transaction.signatures_count}/{config.required_signatures}")

# Подпись вторым владельцем
private_key_2 = "another_private_key_hex"
owner_address_2 = "TXa8BcvFe1234567890abcdefghijklmno"

transaction = multisig.sign_transaction(
    transaction=transaction,
    private_key_hex=private_key_2,
    signer_address=owner_address_2
)

print(f"Готова к отправке: {transaction.is_ready_to_broadcast}")
```

### 4. Подпись через Web кошелек (TronLink)

```python
# Для интеграции с TronLink используйте add_external_signature

# На фронтенде (JavaScript):
# const signature = await tronWeb.trx.sign(transaction);
# Отправьте signature на бэкенд

# На бэкенде (Python):
signature_from_web = "304502..."  # Подпись от TronLink
signer_address = "TYs7MvyFe1234567890abcdefghijklmno"

transaction = multisig.add_external_signature(
    transaction=transaction,
    signature_hex=signature_from_web,
    signer_address=signer_address,
    public_key_hex=None  # Опционально, для верификации
)

print(f"Подписей: {transaction.signatures_count}/{config.required_signatures}")
print(f"Готова к отправке: {transaction.is_ready_to_broadcast}")
```

### 5. Проверка подписей и отправка транзакции

```python
# Проверить все подписи
for sig in transaction.signatures:
    is_valid = multisig.verify_signature(transaction, sig)
    print(f"Подпись от {sig.signer_address}: {is_valid}")

# Объединить подписи в финальную транзакцию
if transaction.is_ready_to_broadcast:
    signed_tx = multisig.combine_signatures(transaction)
    
    print("Подписанная транзакция:")
    print(f"TX ID: {signed_tx['txID']}")
    print(f"Подписи: {len(signed_tx['signature'])}")
    
    # Отправить через TRON API
    # result = tronWeb.trx.sendRawTransaction(signed_tx)
else:
    print(f"Недостаточно подписей: {transaction.signatures_count}/{config.required_signatures}")
```

### 6. Получение информации о весах

```python
weight_info = multisig.get_transaction_weight(transaction)

print(f"Количество подписей: {weight_info['signatures_count']}")
print(f"Требуется подписей: {weight_info['required_signatures']}")

if 'total_weight' in weight_info:
    print(f"Суммарный вес: {weight_info['total_weight']}")
    print(f"Пороговый вес: {weight_info['threshold_weight']}")
    print("Веса подписантов:")
    for address, weight in weight_info['signer_weights'].items():
        print(f"  {address}: {weight}")
```

### 7. Утилиты для работы с адресами

```python
multisig = TronMultisig()

# Конвертация публичного ключа в адрес
pubkey_hex = "04abcdef..."  # 65 байт (130 hex символов)
address = multisig.address_from_pubkey(pubkey_hex)
print(f"TRON адрес: {address}")

# Конвертация base58 в hex
hex_address = multisig.address_to_hex("TYs7MvyFe1234567890abcdefghijklmno")
print(f"Hex адрес: {hex_address}")

# Конвертация hex в base58
base58_address = multisig.hex_to_address("41abcdef...")
print(f"Base58 адрес: {base58_address}")

# Вычисление Transaction ID
raw_data_hex = "0a029a6122..."
tx_id = multisig.calculate_tx_id(raw_data_hex)
print(f"Transaction ID: {tx_id}")
```

---

## 🌐 Интеграция с Web кошельками

### Вариант 1: Vue 2 компонент (Рекомендуется для Vue приложений)

Компонент находится в `static/js/tron-multisig-vue.js` и готов к использованию.

**Подключение в HTML:**

```html
<script src="/static/js/vue.min.js"></script>
<script src="/static/js/tron-multisig-vue.js"></script>
<script src="/static/js/components.js"></script>
```

**Использование:**

```html
<tron-multisig backend-url="/api/multisig"></tron-multisig>
```

Компонент автоматически:
- Подключается к TronLink
- Показывает форму создания транзакции
- Подписывает через TronLink
- Отправляет подпись на backend
- Показывает статус транзакции

См. комментарии в файле `static/js/tron-multisig-vue.js` для всех опций.

### Вариант 2: Vanilla JavaScript (Standalone)

Используйте класс `TronMultisigWeb` из `web_integration.js`:

```javascript
// Инициализация
const multisig = new TronMultisigWeb();
await multisig.init();

// Проверка наличия TronLink
if (typeof window.tronWeb !== 'undefined') {
    console.log('TronLink установлен');
    
    // Получить адрес пользователя
    const userAddress = window.tronWeb.defaultAddress.base58;
    
    // Создать транзакцию
    const transaction = await window.tronWeb.transactionBuilder.sendTrx(
        'TRecipientAddress...',
        1000000,  // 1 TRX
        'TMultisigAddress...'
    );
    
    // Подписать транзакцию через TronLink
    const signedTx = await window.tronWeb.trx.sign(transaction);
    
    // Отправить подпись на бэкенд
    const response = await fetch('/api/multisig/add-signature', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            tx_id: transaction.txID,
            signature: signedTx.signature[0],
            signer_address: userAddress
        })
    });
    
    const result = await response.json();
    console.log(`Подписей: ${result.signatures_count}/${result.required_signatures}`);
}
```

Или используйте удобный метод:

```javascript
const multisig = new TronMultisigWeb();
await multisig.init();

const result = await multisig.completeMultisigTransfer(
    'TMultisigAddress',  // From (multisig)
    'TRecipient',        // To
    1000000              // 1 TRX
);

console.log(result.isReady ? '✓ Готово к отправке' : `⏳ ${result.message}`);
```

### Backend (Python)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.tron import TronMultisig

router = APIRouter()

class AddSignatureRequest(BaseModel):
    tx_id: str
    signature: str
    signer_address: str

@router.post("/api/multisig/add-signature")
async def add_signature(request: AddSignatureRequest):
    """Add signature from web wallet"""
    try:
        multisig = TronMultisig()
        
        # Получить транзакцию из хранилища (БД, Redis, etc.)
        transaction = get_transaction_from_storage(request.tx_id)
        
        # Добавить подпись от web кошелька
        transaction = multisig.add_external_signature(
            transaction=transaction,
            signature_hex=request.signature,
            signer_address=request.signer_address
        )
        
        # Сохранить обновленную транзакцию
        save_transaction_to_storage(transaction)
        
        # Если набрано достаточно подписей - можно отправлять
        if transaction.is_ready_to_broadcast:
            signed_tx = multisig.combine_signatures(transaction)
            # Опционально: автоматически отправить в сеть
            # broadcast_result = await broadcast_to_tron(signed_tx)
        
        return {
            "success": True,
            "signatures_count": transaction.signatures_count,
            "required_signatures": transaction.config.required_signatures,
            "is_ready": transaction.is_ready_to_broadcast
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Полный пример работы

```python
# 1. Создание конфигурации мультиподписи
multisig = TronMultisig()
config = multisig.create_multisig_config(
    required_signatures=2,
    owner_addresses=["TOwner1", "TOwner2", "TOwner3"]
)

# 2. Подготовка транзакции (получена от TRON API)
transaction = multisig.prepare_transaction_for_signing(
    raw_data_hex="0a029a6122...",
    tx_id="abc123def456...",
    config=config
)

# 3. Первый владелец подписывает через TronLink (frontend)
# signature1 = await tronWeb.trx.sign(transaction)

# 4. Добавление подписи от web кошелька (backend)
transaction = multisig.add_external_signature(
    transaction=transaction,
    signature_hex="304502210...",  # От TronLink
    signer_address="TOwner1Address..."
)

# 5. Второй владелец подписывает
transaction = multisig.add_external_signature(
    transaction=transaction,
    signature_hex="3045022100...",  # От TronLink
    signer_address="TOwner2Address..."
)

# 6. Проверка и отправка
if transaction.is_ready_to_broadcast:
    signed_tx = multisig.combine_signatures(transaction)
    # Отправить в TRON сеть
```

---

## 📊 Структура данных

### MultisigConfig

```python
@dataclass
class MultisigConfig:
    required_signatures: int                # N - минимум подписей
    total_owners: int                       # M - всего владельцев
    owner_addresses: List[str]              # Адреса владельцев
    owner_pubkeys: Optional[List[str]]      # Публичные ключи
    threshold_weight: Optional[int]         # Пороговый вес
    owner_weights: Optional[List[int]]      # Веса владельцев
```

### MultisigTransaction

```python
@dataclass
class MultisigTransaction:
    raw_data: str                           # Raw данные транзакции
    tx_id: str                              # ID транзакции
    config: MultisigConfig                  # Конфигурация мультиподписи
    signatures: List[SignatureData]         # Список подписей
    
    # Свойства
    @property
    def signatures_count(self) -> int       # Количество валидных подписей
    
    @property
    def total_weight(self) -> int           # Суммарный вес подписей
    
    @property
    def is_ready_to_broadcast(self) -> bool # Готова ли к отправке
```

### SignatureData

```python
@dataclass
class SignatureData:
    signer_address: str                     # Адрес подписанта
    signature: str                          # Подпись (hex)
    signature_index: int                    # Индекс подписанта
    public_key: Optional[str]               # Публичный ключ
    status: SignatureStatus                 # Статус: PENDING/VALID/INVALID
    weight: int = 1                         # Вес подписи
```

---

## 🔒 Безопасность

1. **Приватные ключи**: Никогда не храните приватные ключи в коде или логах
2. **Проверка подписей**: Всегда проверяйте подписи перед отправкой транзакции
3. **Валидация адресов**: Проверяйте формат TRON адресов перед использованием
4. **Веса**: При использовании взвешенной мультиподписи убедитесь, что пороговый вес корректен
5. **Web кошельки**: Используйте `add_external_signature` для безопасной интеграции без доступа к приватным ключам

---

## ⚠️ Ошибки и исключения

```python
# ValueError если конфигурация невалидна
try:
    config = multisig.create_multisig_config(
        required_signatures=3,
        owner_addresses=["addr1", "addr2"]  # M < N
    )
except ValueError as e:
    print(f"Ошибка: {e}")

# ValueError если подписант не является владельцем
try:
    multisig.sign_transaction(
        transaction=tx,
        private_key_hex="...",
        signer_address="not_an_owner"
    )
except ValueError as e:
    print(f"Ошибка: {e}")

# ValueError если недостаточно подписей
try:
    signed_tx = multisig.combine_signatures(incomplete_tx)
except ValueError as e:
    print(f"Ошибка: {e}")
```

---

## 🧪 Тестирование

```python
# Пример unit теста
def test_multisig_2_of_3():
    multisig = TronMultisig()
    
    # Создание конфигурации
    config = multisig.create_multisig_config(
        required_signatures=2,
        owner_addresses=[
            "TYs7MvyFe1234567890abcdefghijklmno",
            "TXa8BcvFe1234567890abcdefghijklmno",
            "TZd9DezFe1234567890abcdefghijklmno",
        ]
    )
    
    assert config.required_signatures == 2
    assert config.total_owners == 3
    
    # Тестирование подписей
    # ... ваши тесты
```

---

## 📁 Структура пакета

```
services/tron/
├── __init__.py              # Экспорт: TronMultisig, MultisigConfig, etc.
├── multisig.py              # Основной модуль с криптографией (619 строк)
├── example_usage.py         # Примеры использования на Python
└── README.md                # Эта документация

static/js/
└── tron-multisig-vue.js     # Vue 2 компонент для интеграции ⭐
```

---

## 📚 Дополнительная информация

- **Примеры**: См. `example_usage.py` для рабочих примеров на Python
- **Vue компонент**: См. `static/js/tron-multisig-vue.js` для готового UI
- **Установка**: Все зависимости в корневом `requirements.txt`

### Ссылки на документацию TRON:
- [TRON Multisig Documentation](https://developers.tron.network/docs/multi-signature)
- [TRON Account Permissions](https://developers.tron.network/docs/account-permissions)
- [TronWeb Documentation](https://developers.tron.network/docs/tronweb)

---

## 🚀 Что дальше?

1. Установите зависимости: `pip install -r requirements.txt`
2. Запустите примеры: `python services/tron/example_usage.py`
3. Интегрируйте с вашим API
4. Добавьте Web интеграцию с TronLink

---

**Версия:** 1.0.0  
**Лицензия:** См. LICENSE в корне проекта
