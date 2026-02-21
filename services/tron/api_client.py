"""
TRON API Client for interacting with TronGrid
"""
import aiohttp
import base58
import hashlib
import time
from typing import Optional, Dict, Any, List
from collections import defaultdict


# TRON API endpoints
TRON_API_MAINNET = "https://api.trongrid.io"
TRON_API_SHASTA = "https://api.shasta.trongrid.io"  # Testnet
TRON_API_NILE = "https://nile.trongrid.io"  # Testnet


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
        amount_trx: float,
        permission_id: int = None,
        expiration_ms: Optional[int] = None
    ) -> dict:
        """
        Create TRX transfer transaction
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount_trx: Amount in TRX
            permission_id: Permission ID to use (e.g., 2 for multisig active permission)
            expiration_ms: Optional expiration timestamp (ms). If not set, node uses default.
        
        Returns unsigned transaction object
        """
        amount_sun = int(amount_trx * 1_000_000)
        
        data = {
            "owner_address": from_address,
            "to_address": to_address,
            "amount": amount_sun,
            "visible": True
        }
        
        # Add permission_id if specified (for multisig accounts)
        if permission_id is not None:
            data["Permission_id"] = permission_id
        if expiration_ms is not None:
            data["expiration"] = expiration_ms
        
        return await self._post(
            "/wallet/createtransaction",
            data
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
    
    async def get_trc20_balance(
        self,
        address: str,
        contract_address: str,
        decimals: int = 6
    ) -> float:
        """
        Get TRC20 token balance
        
        Args:
            address: Account address to check
            contract_address: TRC20 token contract address
            decimals: Token decimals (6 for USDT/USDC, 18 for most tokens)
            
        Returns:
            Token balance as float
        """
        # Convert address to hex format (without '41' prefix, padded to 32 bytes)
        address_hex = base58.b58decode_check(address.encode()).hex()[2:].zfill(64)
        
        result = await self._post(
            "/wallet/triggersmartcontract",
            {
                "owner_address": address,
                "contract_address": contract_address,
                "function_selector": "balanceOf(address)",
                "parameter": address_hex,
                "visible": True
            }
        )
        
        # Parse constant result
        if "constant_result" in result and result["constant_result"]:
            balance_hex = result["constant_result"][0]
            balance_raw = int(balance_hex, 16)
            return balance_raw / (10 ** decimals)
        
        return 0.0
    
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
        # Convert address to hex format for ABI encoding
        # base58.b58decode_check returns bytes: [0x41 prefix] + [20 bytes address]
        decoded_address = base58.b58decode_check(to_address)
        
        # Extract 20 bytes of address (skip the 0x41 prefix)
        # decoded_address[0] = 0x41 (TRON prefix)
        # decoded_address[1:] = 20 bytes of actual address
        address_bytes = decoded_address[1:]  # Take last 20 bytes
        
        # Convert to hex and pad with zeros on the left to 32 bytes (64 hex chars)
        # ABI requires address in 32 bytes (64 hex chars) with right alignment
        to_address_hex = address_bytes.hex().zfill(64)
        
        # Encode amount as 32-byte hex (uint256)
        amount_hex = f"{amount:064x}"
        
        # Parameter: recipient address (32 bytes) + amount (32 bytes)
        # ABI encoding: address right-aligned, uint256 right-aligned
        parameter = to_address_hex + amount_hex
        
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
    
    async def trigger_smart_contract(
        self,
        owner_address: str,
        contract_address: str,
        function_selector: str,
        parameter: str,
        permission_id: Optional[int] = None,
        expiration_ms: Optional[int] = None,
        fee_limit: int = 30_000_000,
    ) -> dict:
        """
        Trigger smart contract function
        
        Args:
            owner_address: Address that triggers the contract
            contract_address: Smart contract address
            function_selector: Function selector (e.g., "transfer(address,uint256)")
            parameter: Encoded parameters (hex string or comma-separated values)
            permission_id: Permission ID for multisig
            expiration_ms: Optional expiration timestamp (ms). If not set, node uses default.
            fee_limit: Max TRX to spend on fees in SUN (default 30 TRX). Prevents OUT_OF_ENERGY.
        
        Returns:
            Unsigned transaction object
        """
        data = {
            "owner_address": owner_address,
            "contract_address": contract_address,
            "function_selector": function_selector,
            "fee_limit": fee_limit,
            "call_value": 0,
            "visible": True
        }
        
        # Handle parameter format - can be hex string or comma-separated values
        # If comma-separated, convert to hex format
        if "," in parameter and not all(c in "0123456789abcdefABCDEF" for c in parameter.replace(",", "")):
            # Simple conversion for address,amount format
            parts = parameter.split(",")
            if len(parts) == 2:
                # Assume address,amount format
                addr = parts[0].strip()
                amount = int(float(parts[1].strip()))
                
                # Convert address to hex
                try:
                    decoded = base58.b58decode_check(addr)
                    addr_hex = decoded[1:].hex().zfill(64)  # Skip 0x41 prefix, pad to 64 chars
                except:
                    addr_hex = addr.zfill(64)
                
                # Convert amount to hex (32 bytes = 64 hex chars)
                amount_hex = f"{amount:064x}"
                parameter = addr_hex + amount_hex
        
        data["parameter"] = parameter
        
        if permission_id is not None:
            data["Permission_id"] = permission_id
        if expiration_ms is not None:
            data["expiration"] = expiration_ms

        return await self._post(
            "/wallet/triggersmartcontract",
            data
        )


class EmulatorTronAPIClient:
    """
    Эмулятор TronAPIClient для тестирования
    Имитирует поведение реального TRON API, храня состояние в памяти
    
    Использование:
        emulator = EmulatorTronAPIClient(network="shasta")
        emulator.set_balance("TAddress123", 1000.0)  # Установить баланс
        async with emulator as api:
            balance = await api.get_balance("TAddress123")
    """
    
    # Классовые переменные для хранения состояния между экземплярами
    _accounts: Dict[str, Dict[str, Any]] = defaultdict(dict)
    _transactions: Dict[str, Dict[str, Any]] = {}
    _trc20_balances: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))  # address -> contract -> balance
    _trc20_decimals: Dict[str, int] = defaultdict(lambda: 6)  # contract -> decimals
    
    def __init__(self, network: str = "shasta", api_key: Optional[str] = None):
        """
        Initialize mock TRON API client
        
        Args:
            network: "mainnet", "shasta" (testnet), or "nile" (testnet)
            api_key: TronGrid API key (optional, для совместимости)
        """
        self.networks = {
            "mainnet": TRON_API_MAINNET,
            "shasta": TRON_API_SHASTA,
            "nile": TRON_API_NILE
        }
        
        if network not in self.networks:
            raise ValueError(f"Unknown network: {network}")
        
        self.network = network
        self.base_url = self.networks[network]
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass
    
    def _generate_tx_id(self, data: Dict[str, Any]) -> str:
        """Генерирует уникальный txID для транзакции"""
        tx_data = str(data).encode()
        return hashlib.sha256(tx_data + str(time.time()).encode()).hexdigest()
    
    def _ensure_account(self, address: str) -> Dict[str, Any]:
        """Создает аккаунт, если его еще нет"""
        if address not in self._accounts:
            self._accounts[address] = {
                "address": address,
                "balance": 0,  # в SUN
                "active_permission": []
            }
        return self._accounts[address]
    
    async def get_account(self, address: str) -> dict:
        """Get account information"""
        account = self._ensure_account(address)
        return account.copy()
    
    async def get_balance(self, address: str) -> float:
        """Get TRX balance in TRX (not SUN)"""
        account = self._ensure_account(address)
        balance_sun = account.get("balance", 0)
        return balance_sun / 1_000_000  # Convert SUN to TRX
    
    async def create_transaction(
        self,
        from_address: str,
        to_address: str,
        amount_trx: float,
        permission_id: int = None
    ) -> dict:
        """
        Create TRX transfer transaction
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount_trx: Amount in TRX
            permission_id: Permission ID to use (e.g., 2 for multisig active permission)
        
        Returns unsigned transaction object
        """
        amount_sun = int(amount_trx * 1_000_000)
        
        # Проверка баланса
        from_account = self._ensure_account(from_address)
        if from_account["balance"] < amount_sun:
            return {
                "result": False,
                "message": f"Insufficient balance: {from_account['balance']} < {amount_sun}"
            }
        
        # Генерация транзакции
        tx_data = {
            "owner_address": from_address,
            "to_address": to_address,
            "amount": amount_sun,
            "visible": True
        }
        
        if permission_id is not None:
            tx_data["Permission_id"] = permission_id
        
        tx_id = self._generate_tx_id(tx_data)
        
        transaction = {
            "txID": tx_id,
            "raw_data_hex": "0a" + "0" * 198,  # Mock hex data
            "raw_data": {
                "contract": [
                    {
                        "parameter": {
                            "value": {
                                "owner_address": from_address,
                                "to_address": to_address,
                                "amount": amount_sun
                            },
                            "type_url": "type.googleapis.com/protocol.TransferContract"
                        },
                        "type": "TransferContract"
                    }
                ],
                "ref_block_bytes": "0001",
                "ref_block_hash": "0000000000000001",
                "expiration": int(time.time() * 1000) + 3600000,
                "timestamp": int(time.time() * 1000)
            },
            "visible": True
        }
        
        # Сохраняем транзакцию
        self._transactions[tx_id] = {
            "tx_id": tx_id,
            "from": from_address,
            "to": to_address,
            "amount": amount_sun,
            "status": "pending",
            "transaction": transaction
        }
        
        return transaction
    
    async def broadcast_transaction(self, signed_transaction: dict) -> dict:
        """Broadcast signed transaction to network"""
        tx_id = signed_transaction.get("txID")
        if not tx_id:
            return {
                "result": False,
                "message": "Transaction ID not found"
            }
        
        # Находим транзакцию
        if tx_id not in self._transactions:
            return {
                "result": False,
                "message": f"Transaction {tx_id} not found"
            }
        
        tx_info = self._transactions[tx_id]
        
        # Выполняем транзакцию (переводим средства)
        from_address = tx_info["from"]
        to_address = tx_info["to"]
        amount = tx_info["amount"]
        
        from_account = self._ensure_account(from_address)
        to_account = self._ensure_account(to_address)
        
        # Проверка баланса еще раз
        if from_account["balance"] < amount:
            return {
                "result": False,
                "message": f"Insufficient balance: {from_account['balance']} < {amount}"
            }
        
        # Выполняем перевод
        from_account["balance"] -= amount
        to_account["balance"] += amount
        
        # Обновляем статус транзакции
        tx_info["status"] = "confirmed"
        
        return {
            "result": True,
            "txid": tx_id,
            "message": "Success"
        }
    
    async def get_transaction_info(self, tx_id: str) -> dict:
        """Get transaction information by ID"""
        if tx_id not in self._transactions:
            return {
                "result": False,
                "message": f"Transaction {tx_id} not found"
            }
        
        tx_info = self._transactions[tx_id]
        return {
            "id": tx_id,
            "blockNumber": 12345,
            "blockTimeStamp": int(time.time() * 1000),
            "contractResult": [],
            "contract_address": "",
            "receipt": {
                "result": "SUCCESS" if tx_info["status"] == "confirmed" else "PENDING"
            },
            "result": "SUCCESS" if tx_info["status"] == "confirmed" else "PENDING"
        }
    
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
        account = self._ensure_account(owner_address)
        
        # Обновляем active_permission
        if "actives" in permission_data:
            account["active_permission"] = permission_data["actives"]
        elif "active" in permission_data:
            # Если передана одна permission
            if "active_permission" not in account:
                account["active_permission"] = []
            account["active_permission"].append(permission_data["active"])
        
        return {
            "result": True,
            "message": "Success"
        }
    
    async def get_trc20_balance(
        self,
        address: str,
        contract_address: str,
        decimals: int = 6
    ) -> float:
        """
        Get TRC20 token balance
        
        Args:
            address: Account address to check
            contract_address: TRC20 token contract address
            decimals: Token decimals (6 for USDT/USDC, 18 for most tokens)
            
        Returns:
            Token balance as float
        """
        self._ensure_account(address)  # Создаем аккаунт, если нужно
        balance_raw = self._trc20_balances[address][contract_address]
        return balance_raw / (10 ** decimals)
    
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
        # Проверка баланса TRC20
        balance = self._trc20_balances[from_address][contract_address]
        if balance < amount:
            return {
                "result": False,
                "message": f"Insufficient TRC20 balance: {balance} < {amount}"
            }
        
        # Проверка баланса TRX для комиссии
        from_account = self._ensure_account(from_address)
        if from_account["balance"] < fee_limit:
            return {
                "result": False,
                "message": f"Insufficient TRX for fee: {from_account['balance']} < {fee_limit}"
            }
        
        # Генерация транзакции
        tx_data = {
            "owner_address": from_address,
            "contract_address": contract_address,
            "to_address": to_address,
            "amount": amount
        }
        
        tx_id = self._generate_tx_id(tx_data)
        
        # Конвертируем адрес в hex для параметра
        try:
            decoded = base58.b58decode_check(to_address)
            to_address_hex = decoded[1:].hex().zfill(64)  # Skip 0x41 prefix, pad to 64 chars
        except:
            to_address_hex = to_address.zfill(64)
        
        amount_hex = f"{amount:064x}"
        parameter = to_address_hex + amount_hex
        
        transaction = {
            "txID": tx_id,
            "raw_data_hex": "0a" + "0" * 198,
            "raw_data": {
                "contract": [
                    {
                        "parameter": {
                            "value": {
                                "owner_address": from_address,
                                "contract_address": contract_address,
                                "data": parameter,
                                "call_value": 0,
                                "fee_limit": fee_limit
                            },
                            "type_url": "type.googleapis.com/protocol.TriggerSmartContract"
                        },
                        "type": "TriggerSmartContract"
                    }
                ],
                "ref_block_bytes": "0001",
                "ref_block_hash": "0000000000000001",
                "expiration": int(time.time() * 1000) + 3600000,
                "timestamp": int(time.time() * 1000)
            },
            "visible": True
        }
        
        # Сохраняем транзакцию
        self._transactions[tx_id] = {
            "tx_id": tx_id,
            "from": from_address,
            "to": to_address,
            "contract": contract_address,
            "amount": amount,
            "is_trc20": True,
            "status": "pending",
            "transaction": transaction
        }
        
        return transaction
    
    async def trigger_smart_contract(
        self,
        owner_address: str,
        contract_address: str,
        function_selector: str,
        parameter: str,
        permission_id: Optional[int] = None
    ) -> dict:
        """
        Trigger smart contract function (используется в escrow.py)
        
        Args:
            owner_address: Address that triggers the contract
            contract_address: Smart contract address
            function_selector: Function selector (e.g., "transfer(address,uint256)")
            parameter: Encoded parameters (hex string or comma-separated values)
            permission_id: Permission ID for multisig
        """
        # Для transfer функции
        if function_selector == "transfer(address,uint256)":
            # Парсим параметры (может быть hex или comma-separated)
            if "," in parameter and not all(c in "0123456789abcdefABCDEF" for c in parameter.replace(",", "")):
                # Comma-separated format: address,amount
                parts = parameter.split(",")
                if len(parts) == 2:
                    to_address = parts[0].strip()
                    amount = int(float(parts[1].strip()))
                    
                    # Проверка баланса
                    balance = self._trc20_balances[owner_address][contract_address]
                    if balance < amount:
                        return {
                            "result": False,
                            "message": f"Insufficient TRC20 balance: {balance} < {amount}"
                        }
                    
                    # Конвертируем адрес в hex
                    try:
                        decoded = base58.b58decode_check(to_address)
                        to_address_hex = decoded[1:].hex().zfill(64)
                    except:
                        to_address_hex = to_address.zfill(64)
                    
                    amount_hex = f"{amount:064x}"
                    parameter = to_address_hex + amount_hex
            else:
                # Hex format - парсим amount из hex
                if len(parameter) >= 128:
                    amount_hex = parameter[64:128]
                    amount = int(amount_hex, 16)
                    
                    # Проверка баланса
                    balance = self._trc20_balances[owner_address][contract_address]
                    if balance < amount:
                        return {
                            "result": False,
                            "message": f"Insufficient TRC20 balance: {balance} < {amount}"
                        }
        
        # Генерация транзакции
        tx_data = {
            "owner_address": owner_address,
            "contract_address": contract_address,
            "function_selector": function_selector,
            "parameter": parameter
        }
        
        tx_id = self._generate_tx_id(tx_data)
        
        transaction = {
            "txID": tx_id,
            "raw_data_hex": "0a" + "0" * 198,
            "raw_data": {
                "contract": [
                    {
                        "parameter": {
                            "value": {
                                "owner_address": owner_address,
                                "contract_address": contract_address,
                                "function_selector": function_selector,
                                "parameter": parameter,
                                "call_value": 0
                            },
                            "type_url": "type.googleapis.com/protocol.TriggerSmartContract"
                        },
                        "type": "TriggerSmartContract"
                    }
                ],
                "ref_block_bytes": "0001",
                "ref_block_hash": "0000000000000001",
                "expiration": int(time.time() * 1000) + 3600000,
                "timestamp": int(time.time() * 1000)
            },
            "visible": True
        }
        
        # Сохраняем транзакцию
        self._transactions[tx_id] = {
            "tx_id": tx_id,
            "from": owner_address,
            "contract": contract_address,
            "function": function_selector,
            "parameter": parameter,
            "is_trc20": function_selector == "transfer(address,uint256)",
            "status": "pending",
            "transaction": transaction
        }
        
        return transaction
    
    # Вспомогательные методы для управления состоянием в тестах
    
    def set_balance(self, address: str, balance_trx: float):
        """Установить баланс TRX для адреса (для тестирования)"""
        account = self._ensure_account(address)
        account["balance"] = int(balance_trx * 1_000_000)
    
    def set_trc20_balance(
        self,
        address: str,
        contract_address: str,
        balance: float,
        decimals: int = 6
    ):
        """Установить баланс TRC20 токена для адреса (для тестирования)"""
        self._trc20_balances[address][contract_address] = int(balance * (10 ** decimals))
        self._trc20_decimals[contract_address] = decimals
    
    def set_account_permissions(
        self,
        address: str,
        permissions: List[Dict[str, Any]]
    ):
        """Установить permissions для аккаунта (для тестирования)"""
        account = self._ensure_account(address)
        account["active_permission"] = permissions
    
    def clear_state(self):
        """Очистить все состояние (для тестирования)"""
        self._accounts.clear()
        self._transactions.clear()
        self._trc20_balances.clear()
        self._trc20_decimals.clear()
    
    @classmethod
    def reset_global_state(cls):
        """Сбросить глобальное состояние (для тестирования)"""
        cls._accounts.clear()
        cls._transactions.clear()
        cls._trc20_balances.clear()
        cls._trc20_decimals.clear()

