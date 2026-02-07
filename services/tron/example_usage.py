"""
Example usage of TRON Multisig Service with async support

This file demonstrates how to use the multisig service for TRON wallets
"""
import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    # Fallback for older Python versions
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

from multisig import TronMultisig, MultisigConfig, SignatureStatus
import aiohttp
import asyncio
import json
from typing import Optional, Tuple
import hashlib
import hmac
import ecdsa
import base58
from mnemonic import Mnemonic
from tronpy.keys import PrivateKey as TronPrivateKey
from bip32 import BIP32

# TRON API endpoints
TRON_API_MAINNET = "https://api.trongrid.io"
TRON_API_SHASTA = "https://api.shasta.trongrid.io"  # Testnet
TRON_API_NILE = "https://nile.trongrid.io"  # Testnet

# API Key (получите на https://www.trongrid.io/)
TRON_API_KEY = None  # Опционально, но рекомендуется для production


def address_from_private_key(private_key_hex: str) -> str:
    """
    Calculate TRON address from private key using tronpy
    
    Args:
        private_key_hex: Private key as hex string (64 characters)
        
    Returns:
        TRON address (base58 encoded)
    """
    # Use tronpy's PrivateKey class for proper TRON address generation
    priv_key = TronPrivateKey(bytes.fromhex(private_key_hex))
    return priv_key.public_key.to_base58check_address()


def private_key_from_mnemonic(mnemonic: str, passphrase: str = "", account_index: int = 0) -> str:
    """
    Generate TRON private key from mnemonic phrase using BIP39/BIP44
    
    Args:
        mnemonic: Mnemonic phrase (12-24 words)
        passphrase: Optional passphrase (BIP39 standard)
        account_index: Account index in BIP44 path (default: 0)
        
    Returns:
        Private key as hex string (64 characters)
    """
    # Generate BIP39 seed
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed(mnemonic, passphrase)
    
    # Create BIP32 HD wallet from seed
    bip32_ctx = BIP32.from_seed(seed)
    
    # BIP44 path for TRON: m/44'/195'/0'/0/{account_index}
    # 44' - BIP44 purpose
    # 195' - TRON coin type
    # 0' - account (hardened)
    # 0 - external chain (receive)
    # account_index - address index
    path = f"m/44'/195'/0'/0/{account_index}"
    
    # Derive private key using BIP32
    derived_key = bip32_ctx.get_privkey_from_path(path)
    
    return derived_key.hex()


def keypair_from_mnemonic(mnemonic: str, passphrase: str = "", account_index: int = 0) -> Tuple[str, str]:
    """
    Generate TRON address and private key from mnemonic phrase
    
    Args:
        mnemonic: Mnemonic phrase (12-24 words)
        passphrase: Optional passphrase
        account_index: Account index in BIP44 path (default: 0)
        
    Returns:
        Tuple of (address, private_key_hex)
    """
    private_key = private_key_from_mnemonic(mnemonic, passphrase, account_index)
    address = address_from_private_key(private_key)
    return address, private_key


# Generate test keys from mnemonics
# WARNING: These are TEST mnemonics - NEVER use in production!
_owner1_addr, _owner1_key = keypair_from_mnemonic('pyramid copper syrup license leisure language brick core cream grief glass lazy')
_owner2_addr, _owner2_key = keypair_from_mnemonic('destroy render width tilt crunch nerve urban adapt capital access romance salon')
_owner3_addr, _owner3_key = keypair_from_mnemonic('diet dose swamp truth taxi useful text run exotic enforce puzzle hard')

# Test keys for examples (generated for testing only - DO NOT USE IN PRODUCTION)
TEST_KEYS = {
    "owner1": {
        "address": _owner1_addr,
        "private_key": _owner1_key  # First owner can also sign programmatically
    },
    "owner2": {
        "address": _owner2_addr,
        "private_key": _owner2_key
    },
    "owner3": {
        "address": _owner3_addr,
        "private_key": _owner3_key
    }
}

assert TEST_KEYS["owner1"]["address"] == "TBzoUzcPQ2FWsRY4vhNh2nqkrSsYtJkAwY"

print(f"Generated test addresses:")
print(f"  Owner 1: {_owner1_addr}")
print(f"  Owner 2: {_owner2_addr}")
print(f"  Owner 3: {_owner3_addr}")
print()


def example_basic_2_of_3_multisig():
    """Example: Basic 2/3 multisig wallet"""
    print("=" * 60)
    print("Пример 1: Базовая 2/3 мультиподпись")
    print("=" * 60)
    
    # Инициализация сервиса
    multisig = TronMultisig()
    
    # Адреса владельцев (сгенерированы из мнемоник)
    owner_addresses = [
        TEST_KEYS["owner1"]["address"],  # Владелец 1
        TEST_KEYS["owner2"]["address"],  # Владелец 2
        TEST_KEYS["owner3"]["address"],  # Владелец 3
    ]
    
    # Создание конфигурации: нужно 2 подписи из 3
    config = multisig.create_multisig_config(
        required_signatures=2,
        owner_addresses=owner_addresses
    )
    
    print(f"✓ Создана конфигурация {config.required_signatures}/{config.total_owners}")
    print(f"  Владельцев: {config.total_owners}")
    print(f"  Требуется подписей: {config.required_signatures}")
    print()


def example_weighted_multisig():
    """Example: Weighted multisig with different weights"""
    print("=" * 60)
    print("Пример 2: Взвешенная мультиподпись")
    print("=" * 60)
    
    multisig = TronMultisig()
    
    # Настройка весов
    owner_addresses = [
        TEST_KEYS["owner1"]["address"],  # CEO
        TEST_KEYS["owner2"]["address"],  # CTO
        TEST_KEYS["owner3"]["address"],  # Developer
    ]
    
    owner_weights = [3, 2, 1]  # CEO=3, CTO=2, Dev=1
    threshold_weight = 4  # Нужен суммарный вес >= 4
    
    config = multisig.create_multisig_config(
        required_signatures=2,  # Минимум 2 подписи
        owner_addresses=owner_addresses,
        threshold_weight=threshold_weight,
        owner_weights=owner_weights
    )
    
    print(f"✓ Создана взвешенная конфигурация")
    print(f"  Пороговый вес: {config.threshold_weight}")
    print(f"  Веса владельцев:")
    for addr, weight in zip(config.owner_addresses, config.owner_weights):
        print(f"    {addr[:10]}...: вес {weight}")
    print()
    print(f"  Возможные комбинации:")
    print(f"    CEO (3) + CTO (2) = 5 ≥ 4 ✓")
    print(f"    CEO (3) + Dev (1) = 4 ≥ 4 ✓")
    print(f"    CTO (2) + Dev (1) = 3 < 4 ✗")
    print()


def example_sign_transaction():
    """Example: Signing a transaction"""
    print("=" * 60)
    print("Пример 3: Подпись транзакции")
    print("=" * 60)
    
    multisig = TronMultisig()
    
    # Конфигурация 2/3
    owner_addresses = [
        TEST_KEYS["owner1"]["address"],
        TEST_KEYS["owner2"]["address"],
        TEST_KEYS["owner3"]["address"],
    ]
    
    config = multisig.create_multisig_config(
        required_signatures=2,
        owner_addresses=owner_addresses
    )
    
    # Пример данных транзакции (замените на реальные от TRON API)
    raw_data_hex = "0a029a6122082f1e3ddcc01e45954085f69be8012e5a65080112610a2d747970652e676f6f676c65617069732e636f6d2f70726f746f636f6c2e5472616e73666572436f6e747261637412300a15418840e6c55b9ada326d211d818c34a994aadfbac3121541a7d8a35b260395c14aa456297662092ba3876fc91880ade204"
    tx_id = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    # Подготовка транзакции
    transaction = multisig.prepare_transaction_for_signing(
        raw_data_hex=raw_data_hex,
        tx_id=tx_id,
        config=config,
        contract_type="TransferContract"
    )
    
    print(f"✓ Транзакция подготовлена")
    print(f"  TX ID: {transaction.tx_id[:16]}...")
    print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
    print(f"  Готова к отправке: {transaction.is_ready_to_broadcast}")
    print()
    
    # Подпись вторым владельцем
    print("Подпись вторым владельцем...")
    transaction = multisig.sign_transaction(
        transaction=transaction,
        private_key_hex=TEST_KEYS["owner2"]["private_key"],
        signer_address=TEST_KEYS["owner2"]["address"]
    )
    print(f"  ✓ Подписано владельцем 2")
    print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
    print(f"  Готова к отправке: {transaction.is_ready_to_broadcast}")
    print()
    
    # Подпись третьим владельцем
    print("Подпись третьим владельцем...")
    transaction = multisig.sign_transaction(
        transaction=transaction,
        private_key_hex=TEST_KEYS["owner3"]["private_key"],
        signer_address=TEST_KEYS["owner3"]["address"]
    )
    print(f"  ✓ Подписано владельцем 3")
    print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
    print(f"  Готова к отправке: {transaction.is_ready_to_broadcast}")
    print()
    
    # Объединение подписей
    if transaction.is_ready_to_broadcast:
        signed_tx = multisig.combine_signatures(transaction)
        print("✓ Транзакция подписана и готова к отправке!")
        print(f"  Всего подписей: {len(signed_tx['signature'])}")
        print(f"  Размер транзакции: {len(str(signed_tx))} байт")
        print()


def example_address_utilities():
    """Example: Address conversion utilities"""
    print("=" * 60)
    print("Пример 4: Утилиты для работы с адресами")
    print("=" * 60)
    
    multisig = TronMultisig()
    
    # Конвертация base58 в hex
    base58_address = TEST_KEYS["owner1"]["address"]
    try:
        hex_address = multisig.address_to_hex(base58_address)
        print(f"Base58: {base58_address}")
        print(f"Hex:    {hex_address}")
        print()
    except Exception as e:
        print(f"Ошибка конвертации: {e}")
        print()
    
    # Вычисление Transaction ID
    raw_data_hex = "0a029a6122082f1e3ddcc01e45954085f69be8012e5a65080112610a2d747970652e676f6f676c65617069732e636f6d2f70726f746f636f6c2e5472616e73666572436f6e747261637412300a15418840e6c55b9ada326d211d818c34a994aadfbac3121541a7d8a35b260395c14aa456297662092ba3876fc91880ade204"
    tx_id = multisig.calculate_tx_id(raw_data_hex)
    print(f"Raw data (начало): {raw_data_hex[:40]}...")
    print(f"Transaction ID:    {tx_id}")
    print()


class TronAPIClient:
    """
    Async client for interacting with TRON blockchain via TronGrid API
    """
    
    def __init__(self, network: str = "shasta", api_key: Optional[str] = None):
        """
        Initialize TRON API client
        
        Args:
            network: "mainnet", "shasta" (testnet), or "nile" (testnet)
            api_key: TronGrid API key (optional but recommended)
        """
        self.networks = {
            "mainnet": TRON_API_MAINNET,
            "shasta": TRON_API_SHASTA,
            "nile": TRON_API_NILE
        }
        
        if network not in self.networks:
            raise ValueError(f"Unknown network: {network}")
        
        self.base_url = self.networks[network]
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        
        if api_key:
            self.headers["TRON-PRO-API-KEY"] = api_key
        
        self.session = None
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _post(self, endpoint: str, data: dict) -> dict:
        """Make POST request to TRON API"""
        if not self.session:
            raise RuntimeError("Use TronAPIClient as async context manager")
        
        url = f"{self.base_url}{endpoint}"
        async with self.session.post(url, json=data) as response:
            return await response.json()
    
    async def get_account(self, address: str) -> dict:
        """Get account information"""
        return await self._post(
            "/wallet/getaccount",
            {"address": address, "visible": True}
        )
    
    async def get_balance(self, address: str) -> float:
        """Get TRX balance in TRX (not SUN)"""
        account = await self.get_account(address)
        balance_sun = account.get("balance", 0)
        return balance_sun / 1_000_000  # Convert SUN to TRX
    
    async def create_transaction(
        self,
        from_address: str,
        to_address: str,
        amount_trx: float
    ) -> dict:
        """
        Create TRX transfer transaction
        
        Returns unsigned transaction object
        """
        amount_sun = int(amount_trx * 1_000_000)
        
        return await self._post(
            "/wallet/createtransaction",
            {
                "owner_address": from_address,
                "to_address": to_address,
                "amount": amount_sun,
                "visible": True
            }
        )
    
    async def broadcast_transaction(self, signed_transaction: dict) -> dict:
        """Broadcast signed transaction to network"""
        return await self._post(
            "/wallet/broadcasttransaction",
            signed_transaction
        )
    
    async def get_transaction_info(self, tx_id: str) -> dict:
        """Get transaction information by ID"""
        return await self._post(
            "/wallet/gettransactioninfobyid",
            {"value": tx_id}
        )
    
    async def update_account_permission(
        self,
        owner_address: str,
        permission_data: dict
    ) -> dict:
        """
        Update account permissions for multisig
        
        Args:
            owner_address: Account address to update
            permission_data: Permission configuration
        """
        data = {
            "owner_address": owner_address,
            "visible": True,
            **permission_data
        }
        
        return await self._post(
            "/wallet/accountpermissionupdate",
            data
        )
    
    async def create_trc20_transaction(
        self,
        from_address: str,
        to_address: str,
        contract_address: str,
        amount: int,
        fee_limit: int = 10_000_000  # 10 TRX maximum fee
    ) -> dict:
        """
        Create TRC20 token transfer transaction
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            contract_address: TRC20 token contract address
            amount: Amount in smallest units (for USDT: 1 USDT = 1,000,000)
            fee_limit: Maximum TRX to spend on fees (in SUN)
            
        Returns:
            Unsigned transaction object
        """
        # Convert address to hex format (remove 'T', add '41' prefix)
        to_address_hex = "41" + base58.b58decode_check(to_address.encode()).hex()[2:]
        
        # Encode amount as 32-byte hex (uint256)
        amount_hex = f"{amount:064x}"
        
        # Parameter: recipient address (32 bytes) + amount (32 bytes)
        parameter = to_address_hex.ljust(64, '0') + amount_hex
        
        return await self._post(
            "/wallet/triggersmartcontract",
            {
                "owner_address": from_address,
                "contract_address": contract_address,
                "function_selector": "transfer(address,uint256)",
                "parameter": parameter,
                "fee_limit": fee_limit,
                "call_value": 0,
                "visible": True
            }
        )


def example_error_handling():
    """Example: Error handling"""
    print("=" * 60)
    print("Пример 5: Обработка ошибок")
    print("=" * 60)
    
    multisig = TronMultisig()
    
    # Ошибка: N > M
    print("Попытка создать конфигурацию с N > M...")
    try:
        config = multisig.create_multisig_config(
            required_signatures=3,
            owner_addresses=[
                "TQRk9YdABF21UbrrSkKzxiRZFexCodqP6R",
                "TDK9FCVF74Fdgmwg5Ks5nstidaUie94c5n",
            ]
        )
    except ValueError as e:
        print(f"✓ Перехвачена ошибка: {e}")
    print()
    
    # Ошибка: Дубликаты адресов
    print("Попытка создать конфигурацию с дубликатами...")
    try:
        config = multisig.create_multisig_config(
            required_signatures=2,
            owner_addresses=[
                "TQRk9YdABF21UbrrSkKzxiRZFexCodqP6R",
                "TQRk9YdABF21UbrrSkKzxiRZFexCodqP6R",  # Дубликат
                "TPAyRQZjYKoyPq9rbZMyNDQgpT6ztjRmXn",
            ]
        )
    except ValueError as e:
        print(f"✓ Перехвачена ошибка: {e}")
    print()
    
    # Ошибка: Невалидный адрес
    print("Попытка создать конфигурацию с невалидным адресом...")
    try:
        config = multisig.create_multisig_config(
            required_signatures=2,
            owner_addresses=[
                "INVALID_ADDRESS",
                "TDK9FCVF74Fdgmwg5Ks5nstidaUie94c5n",
                "TPAyRQZjYKoyPq9rbZMyNDQgpT6ztjRmXn",
            ]
        )
    except ValueError as e:
        print(f"✓ Перехвачена ошибка: {e}")
    print()


async def example_testnet_interaction():
    """Example: Interact with TRON Shasta Testnet (async)"""
    print("=" * 60)
    print("Пример 6: Взаимодействие с TRON Testnet (async)")
    print("=" * 60)
    
    # Use async context manager
    async with TronAPIClient(network="shasta") as api:
        # Test addresses
        test_address1 = TEST_KEYS["owner1"]["address"]
        test_address2 = TEST_KEYS["owner2"]["address"]
        
        # 1. Проверка баланса
        print(f"Проверка баланса адреса {test_address1[:10]}...")
        try:
            balance = await api.get_balance(test_address1)
            print(f"  Баланс: {balance:.6f} TRX")
        except Exception as e:
            print(f"  Ошибка: {e}")
        print()
        
        # 2. Получение информации об аккаунте
        print(f"Информация об аккаунте...")
        try:
            account_info = await api.get_account(test_address1)
            print(f"  Создан: {'Да' if account_info else 'Нет'}")
            if account_info:
                print(f"  Bandwidth: {account_info.get('free_net_usage', 0)}")
                print(f"  Energy: {account_info.get('account_resource', {}).get('energy_usage', 0)}")
        except Exception as e:
            print(f"  Ошибка: {e}")
        print()
        
        # 3. Создание транзакции
        print(f"Создание тестовой транзакции...")
        try:
            unsigned_tx = await api.create_transaction(
                from_address=test_address1,
                to_address=test_address2,
                amount_trx=1.0
            )
            
            if "txID" in unsigned_tx:
                print(f"  ✓ Транзакция создана")
                print(f"  TX ID: {unsigned_tx['txID'][:16]}...")
                print(f"  Raw data hex: {unsigned_tx.get('raw_data_hex', '')[:40]}...")
            else:
                print(f"  Ошибка: {unsigned_tx.get('Error', 'Unknown error')}")
        except Exception as e:
            print(f"  Ошибка: {e}")
        print()
    
    print("💡 Подсказка:")
    print("  - Получите testnet TRX: https://shasta.tronex.io/")
    print("  - TronScan testnet: https://shasta.tronscan.org/")
    print()


async def example_create_real_multisig():
    """Example: Create real multisig account on testnet (async)"""
    print("=" * 60)
    print("Пример 7: Создание реального multisig аккаунта (async)")
    print("=" * 60)
    
    async with TronAPIClient(network="shasta") as api:
        multisig = TronMultisig()
        
        # Адреса владельцев
        owner_addresses = [
            TEST_KEYS["owner1"]["address"],
            TEST_KEYS["owner2"]["address"],
            TEST_KEYS["owner3"]["address"],
        ]
        
        # Создать конфигурацию
        config = multisig.create_multisig_config(
            required_signatures=2,
            owner_addresses=owner_addresses
        )
        
        print(f"✓ Конфигурация 2/3 создана")
        print(f"  Владельцы: {config.total_owners}")
        print(f"  Требуется подписей: {config.required_signatures}")
        print()
        
        # Генерация multisig адреса
        multisig_addr = multisig.generate_multisig_address(
            owner_addresses=owner_addresses,
            required_signatures=2,
            salt="example_demo"
        )
        
        print(f"✓ Multisig адрес сгенерирован")
        print(f"  Адрес: {multisig_addr.address}")
        print(f"  Hex: {multisig_addr.hex_address}")
        print()
        
        # Подготовка данных для Account Permission Update
        permission_data = {
            "actives": [{
                "type": 2,
                "permission_name": "multisig_2_of_3",
                "threshold": config.required_signatures,
                "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                "keys": [
                    {"address": addr, "weight": 1}
                    for addr in owner_addresses
                ]
            }]
        }
        
        print("Данные для настройки multisig permissions:")
        print(json.dumps(permission_data, indent=2))
        print()
        
        print("⚠️  Для применения permissions нужно:")
        print("  1. Подписать транзакцию владельцем аккаунта")
        print("  2. Отправить через broadcasttransaction")
        print()
        
        # Попытка создать транзакцию обновления permissions
        print("Создание транзакции обновления permissions...")
        try:
            update_tx = await api.update_account_permission(
                owner_address=owner_addresses[0],
                permission_data=permission_data
            )
            
            if "txID" in update_tx:
                print(f"  ✓ Транзакция обновления создана: {update_tx['txID'][:16]}...")
                print(f"  Raw data hex: {update_tx.get('raw_data_hex', '')[:40]}...")
                print()
                print("  📝 Для завершения нужно:")
                print(f"     1. Подписать транзакцию приватным ключом {owner_addresses[0][:10]}...")
                print(f"     2. Отправить через broadcast_transaction()")
            else:
                error_msg = update_tx.get('Error', 'Unknown error')
                print(f"  ⚠️  Ошибка создания: {error_msg}")
                if "no OwnerAccount" in error_msg:
                    print(f"     Адрес {owner_addresses[0][:10]}... не активирован на testnet")
                    print(f"     Пополните через https://shasta.tronex.io/")
        except Exception as e:
            print(f"  ❌ Исключение: {e}")
        print()


async def example_full_multisig_workflow():
    """Example: Complete multisig workflow with testnet (async)"""
    print("=" * 60)
    print("Пример 8: Полный workflow multisig с testnet (async)")
    print("=" * 60)
    
    async with TronAPIClient(network="shasta") as api:
        multisig = TronMultisig()
        
        # Адреса
        owner1_address = TEST_KEYS["owner1"]["address"]
        owner2_address = TEST_KEYS["owner2"]["address"]
        owner3_address = TEST_KEYS["owner3"]["address"]
        
        config = multisig.create_multisig_config(
            required_signatures=2,
            owner_addresses=[owner1_address, owner2_address, owner3_address]
        )
        
        print("Шаг 1: Создание транзакции")
        print("-" * 40)
        
        recipient = TEST_KEYS["owner3"]["address"]
        amount = 1.0
        
        print(f"  Отправка {amount} TRX")
        print(f"  Из: {owner1_address[:10]}...")
        print(f"  Кому: {recipient[:10]}...")
        print()
        
        try:
            unsigned_tx = await api.create_transaction(
                from_address=owner1_address,
                to_address=recipient,
                amount_trx=amount
            )
            
            if "txID" not in unsigned_tx:
                print(f"❌ Ошибка: {unsigned_tx}")
                return
            
            tx_id = unsigned_tx["txID"]
            raw_data_hex = unsigned_tx["raw_data_hex"]
            
            print(f"  ✓ Транзакция создана: {tx_id[:16]}...")
            print()
            
            # Подготовка для multisig
            print("Шаг 2: Подготовка для multisig")
            print("-" * 40)
            
            transaction = multisig.prepare_transaction_for_signing(
                raw_data_hex=raw_data_hex,
                tx_id=tx_id,
                config=config,
                contract_type="TransferContract"
            )
            
            print(f"  Требуется подписей: {config.required_signatures}")
            print(f"  Текущих подписей: {transaction.signatures_count}")
            print(f"  Готова к broadcast: {transaction.is_ready_to_broadcast}")
            print()
            
            print("Шаг 3: Сбор подписей")
            print("-" * 40)
            
            # Подписать транзакцию владельцами (у которых есть ключи)
            transaction = multisig.sign_transaction(
                transaction=transaction,
                private_key_hex=TEST_KEYS["owner2"]["private_key"],
                signer_address=TEST_KEYS["owner2"]["address"]
            )
            print(f"  ✓ Подписано владельцем 2")
            print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
            
            transaction = multisig.sign_transaction(
                transaction=transaction,
                private_key_hex=TEST_KEYS["owner3"]["private_key"],
                signer_address=TEST_KEYS["owner3"]["address"]
            )
            print(f"  ✓ Подписано владельцем 3")
            print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
            print(f"  Готова к broadcast: {transaction.is_ready_to_broadcast}")
            print()
            
            # Шаг 4: Отправка транзакции в сеть
            if transaction.is_ready_to_broadcast:
                print("Шаг 4: Отправка транзакции в сеть")
                print("-" * 40)
                
                signed_tx = multisig.combine_signatures(transaction)
                result = await api.broadcast_transaction(signed_tx)
                
                if result.get("result"):
                    print(f"  ✓ Транзакция отправлена!")
                    print(f"  TX ID: {result.get('txid', tx_id)}")
                    print()
                    
                    # Шаг 5: Проверка статуса транзакции
                    print("Шаг 5: Проверка статуса транзакции")
                    print("-" * 40)
                    print("  Ожидание подтверждения (3 сек)...")
                    
                    await asyncio.sleep(3)
                    
                    tx_info = await api.get_transaction_info(tx_id)
                    if tx_info:
                        receipt = tx_info.get('receipt', {})
                        print(f"  ✓ Транзакция найдена")
                        print(f"  Статус: {receipt.get('result', 'UNKNOWN')}")
                        print(f"  Блок: {tx_info.get('blockNumber', 'N/A')}")
                        print(f"  Energy использовано: {receipt.get('energy_usage', 0)}")
                        print(f"  Net использовано: {receipt.get('net_usage', 0)}")
                    else:
                        print(f"  ⚠️  Транзакция еще не подтверждена")
                    print()
                else:
                    print(f"  ❌ Ошибка отправки: {result}")
                    print()
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")


async def example_send_trc20_usdt():
    """Example: Send USDT (TRC20 token)"""
    print("=" * 60)
    print("Пример 9: Отправка USDT (TRC20 токен)")
    print("=" * 60)
    
    async with TronAPIClient(network="shasta") as api:
        # Адреса
        from_addr = TEST_KEYS["owner1"]["address"]
        to_addr = TEST_KEYS["owner2"]["address"]
        
        # USDT контракт на Shasta testnet (тестовый TRC20 токен)
        # Mainnet USDT: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
        usdt_contract = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"
        
        # Отправить 10 USDT (USDT имеет 6 decimals: 10 * 10^6)
        amount = 10 * 1_000_000
        
        print(f"Отправка 10 USDT (TRC20)")
        print(f"  Из: {from_addr[:10]}...")
        print(f"  Кому: {to_addr[:10]}...")
        print(f"  Контракт: {usdt_contract[:10]}...")
        print()
        
        try:
            unsigned_tx = await api.create_trc20_transaction(
                from_address=from_addr,
                to_address=to_addr,
                contract_address=usdt_contract,
                amount=amount,
                fee_limit=15_000_000  # 15 TRX fee limit
            )
            
            if "transaction" in unsigned_tx:
                tx_data = unsigned_tx["transaction"]
                print(f"  ✓ Транзакция создана")
                print(f"  TX ID: {tx_data.get('txID', 'N/A')[:16]}...")
                print(f"  Energy: {unsigned_tx.get('energy_used', 0)}")
                print()
                print("  📝 Для отправки нужно:")
                print("     1. Подписать транзакцию")
                print("     2. Отправить через broadcast_transaction()")
            else:
                error_msg = unsigned_tx.get('Error', 'Unknown error')
                print(f"  ⚠️  Ошибка: {error_msg}")
                if "no OwnerAccount" in error_msg:
                    print(f"     Адрес не активирован. Пополните через https://shasta.tronex.io/")
        except Exception as e:
            print(f"  ❌ Исключение: {e}")
        print()
        
        print("💡 Информация о TRC20:")
        print("  - USDT (Mainnet): TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
        print("  - USDC (Mainnet): TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8")
        print("  - Decimals: USDT/USDC = 6, большинство токенов = 18")
        print("  - Energy: ~15,000-30,000 для transfer()")
        print()


async def example_parallel_requests():
    """Example: Parallel requests with asyncio"""
    print("=" * 60)
    print("Пример 10: Параллельные запросы (async)")
    print("=" * 60)
    
    async with TronAPIClient(network="shasta") as api:
        addresses = [
            "TQRk9YdABF21UbrrSkKzxiRZFexCodqP6R",
            "TDK9FCVF74Fdgmwg5Ks5nstidaUie94c5n",
            "TPAyRQZjYKoyPq9rbZMyNDQgpT6ztjRmXn",
        ]
        
        print(f"Проверка балансов {len(addresses)} адресов параллельно...")
        
        # Параллельный запрос балансов
        tasks = [api.get_balance(addr) for addr in addresses]
        balances = await asyncio.gather(*tasks, return_exceptions=True)
        
        print()
        for addr, balance in zip(addresses, balances):
            if isinstance(balance, Exception):
                print(f"  {addr[:10]}...: Ошибка - {balance}")
            else:
                print(f"  {addr[:10]}...: {balance:.6f} TRX")
        print()
        
        print("✓ Все запросы выполнены параллельно!")
        print(f"⚡ Преимущество: ~{len(addresses)}x быстрее чем последовательно")
        print()


async def main_async():
    """Run all async examples"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "TRON Multisig Service - Примеры" + " " * 16 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    try:
        # Базовые примеры (оффлайн)
        example_basic_2_of_3_multisig()
        example_weighted_multisig()
        example_sign_transaction()
        example_address_utilities()
        example_error_handling()
        
        # Async примеры с сетью
        print("\n" + "=" * 60)
        print("Async примеры с TRON сетью (Testnet)")
        print("=" * 60 + "\n")
        
        await example_testnet_interaction()
        await example_create_real_multisig()
        await example_full_multisig_workflow()
        await example_send_trc20_usdt()
        await example_parallel_requests()
        
        print("=" * 60)
        print("Все примеры выполнены!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Entry point - run async main"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

