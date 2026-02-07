"""
TRON-specific test fixtures and mocks
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional


@pytest.fixture
def mock_tron_api_response():
    """
    Factory fixture for creating mock TRON API responses
    """
    def _create_response(
        address: str,
        balance: float = 1000.0,
        has_permissions: bool = True,
        participants: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Create mock account response
        
        Args:
            address: Account address
            balance: TRX balance in TRX (will be converted to SUN)
            has_permissions: Whether account has multisig permissions set
            participants: List of participant addresses (if None, defaults to empty)
        """
        response = {
            "address": address,
            "balance": int(balance * 1_000_000),  # Convert to SUN
        }
        
        if has_permissions and participants:
            # Active permission structure matches real TRON blockchain response
            # Type 2 = Active permission (operations), Type 0 = Owner permission
            response["active_permission"] = [
                {
                    "type": 2,  # Active permission type (number, not string)
                    "id": 2,    # Permission ID (used in transactions)
                    "permission_name": "active",  # Can be custom like "multisig_2_of_3"
                    "threshold": 2,  # Required signature weight
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": [
                        {
                            "address": addr,
                            "weight": 1
                        }
                        for addr in participants
                    ]
                }
            ]
        
        return response
    
    return _create_response


@pytest.fixture
def mock_tron_transaction():
    """
    Factory fixture for creating mock transaction responses
    """
    def _create_transaction(
        tx_id: str = "test_tx_id_123456789",
        from_address: str = "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy",  # Valid TRON address
        to_address: str = "TZ4UXDV5ZhNW7fb2AMSbgfAEZ7hWsnYS2g",      # Valid TRON address
        amount: float = 100.0,
        is_trc20: bool = False
    ) -> Dict[str, Any]:
        """
        Create mock transaction
        
        Args:
            tx_id: Transaction ID
            from_address: Sender address
            to_address: Recipient address
            amount: Amount
            is_trc20: Whether this is TRC20 transaction
        """
        return {
            "txID": tx_id,
            "raw_data_hex": "0a" + "0" * 198,  # Mock hex data
            "raw_data": {
                "contract": [
                    {
                        "parameter": {
                            "value": {
                                "owner_address": from_address,
                                "to_address": to_address,
                                "amount": int(amount * 1_000_000) if not is_trc20 else int(amount * 1e6)
                            },
                            "type_url": "type.googleapis.com/protocol.TriggerSmartContract" if is_trc20 else "type.googleapis.com/protocol.TransferContract"
                        },
                        "type": "TriggerSmartContract" if is_trc20 else "TransferContract"
                    }
                ],
                "ref_block_bytes": "0001",
                "ref_block_hash": "0000000000000001",
                "expiration": 1234567890000,
                "timestamp": 1234567890000
            },
            "visible": True
        }
    
    return _create_transaction


@pytest.fixture
def mock_api_client(mock_tron_api_response, mock_tron_transaction):
    """
    Mock TronAPIClient with common responses
    Uses valid TRON addresses
    """
    mock_client = AsyncMock()
    
    # Valid TRON addresses for defaults
    default_addr1 = "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy"
    default_addr2 = "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW"
    default_addr3 = "TEEXEWrkMFKapSMJ6mErg39ELFKDqEs6w3"
    default_recipient = "TZ4UXDV5ZhNW7fb2AMSbgfAEZ7hWsnYS2g"
    
    # Default responses
    mock_client.get_account = AsyncMock(return_value=mock_tron_api_response(
        address=default_addr1,
        balance=1000.0,
        has_permissions=True,
        participants=[default_addr1, default_addr2, default_addr3]
    ))
    
    mock_client.get_balance = AsyncMock(return_value=1000.0)
    
    mock_client.get_trc20_balance = AsyncMock(return_value=500.0)
    
    mock_client.create_transaction = AsyncMock(return_value=mock_tron_transaction(
        tx_id="test_trx_tx_123",
        from_address=default_addr1,
        to_address=default_recipient,
        amount=100.0
    ))
    
    mock_client.trigger_smart_contract = AsyncMock(return_value=mock_tron_transaction(
        tx_id="test_trc20_tx_123",
        from_address=default_addr1,
        to_address=default_recipient,
        amount=50.0,
        is_trc20=True
    ))
    
    # Mock context manager
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    return mock_client


@pytest.fixture
def patch_tron_api_client(mock_api_client):
    """
    Patch TronAPIClient to return mock client
    """
    with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
        yield mock_api_client


@pytest.fixture
def sample_addresses():
    """
    Sample TRON addresses for testing
    These are valid TRON addresses (base58 encoded, 34 characters)
    """
    return {
        "participant1": "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy",  # Valid TRON address
        "participant2": "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW",  # Valid TRON address
        "arbiter": "TEEXEWrkMFKapSMJ6mErg39ELFKDqEs6w3",        # Valid TRON address
        "recipient": "TZ4UXDV5ZhNW7fb2AMSbgfAEZ7hWsnYS2g",      # Valid TRON address
        "token_contract": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # Valid TRON USDT contract
    }

