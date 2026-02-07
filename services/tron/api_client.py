"""
TRON API Client for interacting with TronGrid
"""
import aiohttp
import base58
from typing import Optional


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
        
        data = {
            "owner_address": from_address,
            "to_address": to_address,
            "amount": amount_sun,
            "visible": True
        }
        
        # Add permission_id if specified (for multisig accounts)
        if permission_id is not None:
            data["Permission_id"] = permission_id
        
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

