"""
Tests for EscrowService with mocked TRON API
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from services.tron.escrow import EscrowService, EscrowError
from db.models import EscrowModel


class TestEscrowInitialization:
    """Test escrow initialization flow"""
    
    @pytest.mark.asyncio
    async def test_create_new_escrow(self, test_db, sample_addresses, mock_api_client):
        """Test creating a new escrow"""
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            
            assert escrow.id is not None
            assert escrow.blockchain == "tron"
            assert escrow.network == "mainnet"
            assert escrow.escrow_type == "multisig"
            assert escrow.escrow_address == sample_addresses["arbiter"]
            assert escrow.arbiter_address == sample_addresses["arbiter"]
            assert escrow.status == "pending"
            
            # Check multisig config
            config = escrow.multisig_config
            assert config["required_signatures"] == 2
            assert config["total_owners"] == 3
            assert set(config["owner_addresses"]) == {
                sample_addresses["participant1"],
                sample_addresses["participant2"],
                sample_addresses["arbiter"]
            }
            
            # Check address roles
            roles = escrow.address_roles
            assert roles[sample_addresses["participant1"]] == "participant"
            assert roles[sample_addresses["participant2"]] == "participant"
            assert roles[sample_addresses["arbiter"]] == "arbiter"
    
    @pytest.mark.asyncio
    async def test_find_existing_escrow_order_independent(self, test_db, sample_addresses, mock_api_client):
        """Test that participant order doesn't matter when finding escrow"""
        # Mock API to return no permissions (so it won't try to verify blockchain)
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            # Create escrow with participant1, participant2
            escrow1 = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            
            # Mark as active to avoid pending timeout
            escrow1.status = "active"
            await test_db.commit()
            
            # Try to initialize with participant2, participant1 (reversed order)
            # Should find the existing escrow, not create a new one
            escrow2 = await service.initialize_escrow(
                participant1=sample_addresses["participant2"],  # Reversed
                participant2=sample_addresses["participant1"],  # Reversed
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            
            # Should find the same escrow
            assert escrow1.id == escrow2.id
    
    @pytest.mark.asyncio
    async def test_inactive_escrows_excluded_from_search(self, test_db, sample_addresses, mock_api_client):
        """Test that inactive escrows are not returned"""
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            # Create and mark as inactive
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            escrow.status = "inactive"
            await test_db.commit()
            
            # Use different arbiter for new escrow to avoid unique constraint
            new_arbiter = "TGzz8gjYiYRqpfmDwnLxfgPuLVNmpCswVp"  # Different valid TRON address
            
            # Try to initialize again - should create new escrow (with different arbiter)
            new_escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=new_arbiter,
                blockchain="tron",
                network="mainnet"
            )
            
            # Should be a different escrow
            assert new_escrow.id != escrow.id
            assert new_escrow.arbiter_address == new_arbiter


class TestEscrowVerification:
    """Test escrow verification against blockchain"""
    
    @pytest.mark.asyncio
    async def test_verify_with_matching_permissions(self, test_db, sample_addresses, mock_api_client):
        """Test verification when blockchain permissions match participants"""
        # Use unique arbiter for this test (using recipient address as arbiter)
        test_arbiter = sample_addresses["recipient"]
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            # First, create escrow without permissions
            mock_api_client.get_account.return_value = {
                "address": test_arbiter,
                "balance": 1000000000
            }
            
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=test_arbiter,
                blockchain="tron",
                network="mainnet"
            )
            
            # Mark as active to avoid pending timeout
            escrow.status = "active"
            await test_db.commit()
            
            # Now set up API mock to return matching permissions
            mock_api_client.get_account.return_value = {
                "address": test_arbiter,
                "balance": 1000000000,  # Balance in SUN (1000 TRX)
                "active_permission": [
                    {
                        "type": 2,  # Active permission type (number)
                        "id": 2,
                        "permission_name": "active",
                        "threshold": 2,
                        "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                        "keys": [
                            {"address": sample_addresses["participant1"], "weight": 1},
                            {"address": sample_addresses["participant2"], "weight": 1},
                            {"address": test_arbiter, "weight": 1}
                        ]
                    }
                ]
            }
            
            # Re-initialize - should find existing and verify permissions
            verified_escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=test_arbiter,
                blockchain="tron",
                network="mainnet"
            )
            await test_db.commit()
            
            # Should be marked as active after verification
            assert verified_escrow.id == escrow.id
            assert verified_escrow.status == "active"
    
    @pytest.mark.asyncio
    async def test_verify_with_changed_arbiter(self, test_db, sample_addresses, mock_api_client):
        """Test auto-detection of changed arbiter from blockchain"""
        # Use unique arbiter for this test
        test_arbiter = "TGzz8gjYiYRqpfmDwnLxfgPuLVNmpCswVp"
        # New arbiter in blockchain (valid TRON address)
        new_arbiter = "TSmpwW3qsqQ7RuB3SxCXvJCH7JJkpBsySy"
        
        # First, create escrow without permissions
        mock_api_client.get_account.return_value = {
            "address": test_arbiter,
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=test_arbiter,
                blockchain="tron",
                network="mainnet"
            )
            
            # Mark as active to avoid pending timeout
            escrow.status = "active"
            await test_db.commit()
        
        # Now mock API to return different arbiter in permissions
        mock_api_client.get_account.return_value = {
            "address": test_arbiter,
            "balance": 1000000000,  # Balance in SUN
            "active_permission": [
                {
                    "type": 2,  # Active permission type
                    "id": 2,
                    "permission_name": "active",
                    "threshold": 2,
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": [
                        {"address": sample_addresses["participant1"], "weight": 1},
                        {"address": sample_addresses["participant2"], "weight": 1},
                        {"address": new_arbiter, "weight": 1}  # Different arbiter
                    ]
                }
            ]
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            # Re-initialize to trigger verification with new arbiter
            verified_escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=test_arbiter,  # Old arbiter in params
                blockchain="tron",
                network="mainnet"
            )
        
        await test_db.refresh(verified_escrow)
        
        # Arbiter should be auto-updated
        assert verified_escrow.arbiter_address == new_arbiter
        assert verified_escrow.address_roles[new_arbiter] == "arbiter"
        assert new_arbiter in verified_escrow.multisig_config["owner_addresses"]
    
    @pytest.mark.asyncio
    async def test_verify_missing_participant_raises_error(self, test_db, sample_addresses, mock_api_client):
        """Test that missing participant raises an error"""
        # Use unique arbiter for this test (using token_contract address as arbiter)
        test_arbiter = sample_addresses["token_contract"]
        
        # First create escrow without permissions
        mock_api_client.get_account.return_value = {
            "address": test_arbiter,
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=test_arbiter,
                blockchain="tron",
                network="mainnet"
            )
            
            # Mark as active to avoid pending timeout
            escrow.status = "active"
            await test_db.commit()
        
        # Now mock API to return permissions WITHOUT participant2 (real TRON structure)
        mock_api_client.get_account.return_value = {
            "address": test_arbiter,
            "balance": 1000000000,  # Balance in SUN
            "active_permission": [
                {
                    "type": 2,  # Active permission type
                    "id": 2,
                    "permission_name": "active",
                    "threshold": 2,
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": [
                        {"address": sample_addresses["participant1"], "weight": 1},
                        {"address": test_arbiter, "weight": 1},
                        {"address": "TGzz8gjYiYRqpfmDwnLxfgPuLVNmpCswVp", "weight": 1}  # Valid TRON address
                    ]
                }
            ]
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            with pytest.raises(EscrowError) as exc_info:
                # Re-initialize should trigger verification and raise error
                await service.initialize_escrow(
                    participant1=sample_addresses["participant1"],
                    participant2=sample_addresses["participant2"],
                    arbiter=test_arbiter,
                    blockchain="tron",
                    network="mainnet"
                )
        
        assert exc_info.value.code == service.PERMISSIONS_MISMATCH
        assert sample_addresses["participant2"] in str(exc_info.value)


class TestEscrowPendingTimeout:
    """Test pending escrow timeout handling"""
    
    @pytest.mark.asyncio
    async def test_pending_timeout_marks_inactive(self, test_db, sample_addresses, mock_api_client):
        """Test that pending escrow times out and gets marked as inactive"""
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            # Create escrow
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            await test_db.commit()
            
            # Verify it's pending
            assert escrow.status == "pending"
            
            # Try to find with immediate timeout
            found = await service._check_existing_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                blockchain="tron",
                network="mainnet",
                wait_if_pending=True,
                timeout_seconds=0  # Immediate timeout
            )
            
            # Should return None and mark as inactive
            assert found is None
            
            # Commit to save the status change
            await test_db.commit()
            await test_db.refresh(escrow)
            assert escrow.status == "inactive"


class TestPaymentTransactions:
    """Test payment transaction creation"""
    
    @pytest.mark.asyncio
    async def test_create_trx_transaction(self, test_db, sample_addresses, mock_api_client, mock_tron_transaction):
        """Test creating TRX payment transaction"""
        service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
        
        # Create and activate escrow
        escrow = await service.initialize_escrow(
            participant1=sample_addresses["participant1"],
            participant2=sample_addresses["participant2"],
            arbiter=sample_addresses["arbiter"],
            blockchain="tron",
            network="mainnet"
        )
        escrow.status = "active"
        await test_db.commit()
        
        # Mock API responses (real TRON structure)
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000,  # Balance in SUN
            "active_permission": [
                {
                    "type": 2,  # Active permission type
                    "id": 2,
                    "permission_name": "active",
                    "threshold": 2,
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": []  # Keys not needed for this test
                }
            ]
        }
        
        mock_api_client.create_transaction.return_value = mock_tron_transaction(
            tx_id="test_trx_tx",
            from_address=sample_addresses["arbiter"],
            to_address=sample_addresses["recipient"],
            amount=100.0
        )
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            result = await service.create_payment_transaction(
                escrow_id=escrow.id,
                to_address=sample_addresses["recipient"],
                amount=100.0,
                token_contract=None
            )
        
        assert result["escrow_id"] == escrow.id
        assert result["required_signatures"] == 2
        assert result["unsigned_tx"]["txID"] == "test_trx_tx"
        assert len(result["participants"]) == 2
        assert result["arbiter"] == sample_addresses["arbiter"]
    
    @pytest.mark.asyncio
    async def test_create_trc20_transaction(self, test_db, sample_addresses, mock_api_client, mock_tron_transaction):
        """Test creating TRC20 payment transaction"""
        service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
        
        # Create and activate escrow
        escrow = await service.initialize_escrow(
            participant1=sample_addresses["participant1"],
            participant2=sample_addresses["participant2"],
            arbiter=sample_addresses["arbiter"],
            blockchain="tron",
            network="mainnet"
        )
        escrow.status = "active"
        await test_db.commit()
        
        # Mock API responses (real TRON structure)
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000,  # Balance in SUN
            "active_permission": [
                {
                    "type": 2,  # Active permission type
                    "id": 2,
                    "permission_name": "active",
                    "threshold": 2,
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": []  # Keys not needed for this test
                }
            ]
        }
        
        mock_api_client.trigger_smart_contract.return_value = mock_tron_transaction(
            tx_id="test_trc20_tx",
            from_address=sample_addresses["arbiter"],
            to_address=sample_addresses["recipient"],
            amount=50.0,
            is_trc20=True
        )
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            result = await service.create_payment_transaction(
                escrow_id=escrow.id,
                to_address=sample_addresses["recipient"],
                amount=50.0,
                token_contract=sample_addresses["token_contract"]
            )
        
        assert result["escrow_id"] == escrow.id
        assert result["unsigned_tx"]["txID"] == "test_trc20_tx"
    
    @pytest.mark.asyncio
    async def test_insufficient_balance_raises_error(self, test_db, sample_addresses, mock_api_client):
        """Test that insufficient balance raises an error"""
        service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
        
        # Create and activate escrow
        escrow = await service.initialize_escrow(
            participant1=sample_addresses["participant1"],
            participant2=sample_addresses["participant2"],
            arbiter=sample_addresses["arbiter"],
            blockchain="tron",
            network="mainnet"
        )
        escrow.status = "active"
        await test_db.commit()
        
        # Mock API with low balance (real TRON structure)
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 10000000,  # 10 TRX in SUN
            "active_permission": [
                {
                    "type": 2,
                    "id": 2,
                    "permission_name": "active",
                    "threshold": 2,
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": []
                }
            ]
        }
        mock_api_client.get_balance.return_value = 10.0  # 10 TRX
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            with pytest.raises(EscrowError) as exc_info:
                await service.create_payment_transaction(
                    escrow_id=escrow.id,
                    to_address=sample_addresses["recipient"],
                    amount=100.0,  # Trying to send 100 TRX
                    token_contract=None
                )
        
        assert exc_info.value.code == service.INSUFFICIENT_BALANCE


class TestEscrowManagement:
    """Test escrow management operations"""
    
    @pytest.mark.asyncio
    async def test_get_escrow_by_id(self, test_db, sample_addresses, mock_api_client):
        """Test retrieving escrow by ID"""
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            await test_db.commit()
            
            retrieved = await service.get_escrow_by_id(escrow.id)
            assert retrieved.id == escrow.id
            assert retrieved.escrow_address == escrow.escrow_address
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_escrow_raises_error(self, test_db):
        """Test that getting non-existent escrow raises error"""
        service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
        
        with pytest.raises(EscrowError) as exc_info:
            await service.get_escrow_by_id(99999)
        
        assert exc_info.value.code == service.ESCROW_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_escrow_balance(self, test_db, sample_addresses, mock_api_client):
        """Test getting escrow balance"""
        service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            await test_db.commit()
            
            mock_api_client.get_balance.return_value = 500.0
            
            balance = await service.get_escrow_balance(escrow.id)
        
        assert balance["escrow_id"] == escrow.id
        assert balance["escrow_address"] == sample_addresses["arbiter"]
        assert balance["trx_balance"] == 500.0
    
    @pytest.mark.asyncio
    async def test_update_arbiter(self, test_db, sample_addresses, mock_api_client):
        """Test updating arbiter address"""
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            await test_db.commit()
            
            new_arbiter = "TGzz8gjYiYRqpfmDwnLxfgPuLVNmpCswVp"  # Valid TRON address
            updated = await service.update_arbiter(escrow.id, new_arbiter)
            
            await test_db.refresh(updated)
            
            assert updated.arbiter_address == new_arbiter
            assert updated.address_roles[new_arbiter] == "arbiter"
            assert new_arbiter in updated.multisig_config["owner_addresses"]
    
    @pytest.mark.asyncio
    async def test_update_escrow_status(self, test_db, sample_addresses, mock_api_client):
        """Test updating escrow status"""
        mock_api_client.get_account.return_value = {
            "address": sample_addresses["arbiter"],
            "balance": 1000000000
        }
        
        with patch('services.tron.escrow.TronAPIClient', return_value=mock_api_client):
            service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
            
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="mainnet"
            )
            await test_db.commit()
            
            assert escrow.status == "pending"
            
            updated = await service.update_escrow_status(escrow.id, "active", tx_id="test_tx_123")
            
            await test_db.refresh(updated)
            assert updated.status == "active"


class TestAPIClientCreation:
    """Test dynamic API client creation"""
    
    @pytest.mark.asyncio
    async def test_api_client_created_per_network(self, test_db, sample_addresses):
        """Test that API client is created dynamically for the correct network"""
        service = EscrowService(session=test_db, owner_did="did:test:owner1", api_key="test_api_key")
        
        # Create mock that tracks which network was used
        mock_client = AsyncMock()
        mock_client.get_account.return_value = {"address": sample_addresses["arbiter"], "balance": 1000000000}
        mock_client.get_balance.return_value = 500.0
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('services.tron.escrow.TronAPIClient') as mock_class:
            mock_class.return_value = mock_client
            
            # Create escrow on shasta network
            escrow = await service.initialize_escrow(
                participant1=sample_addresses["participant1"],
                participant2=sample_addresses["participant2"],
                arbiter=sample_addresses["arbiter"],
                blockchain="tron",
                network="shasta"  # Different network
            )
            await test_db.commit()
            
            # Get balance - should create client with same network
            balance = await service.get_escrow_balance(escrow.id)
            
            # Check that TronAPIClient was called with correct network
            calls = mock_class.call_args_list
            # Should have at least 1 call for get_escrow_balance
            assert len(calls) >= 1
            # All calls should have network='shasta'
            assert all(call.kwargs.get('network') == 'shasta' for call in calls if call.kwargs.get('network'))
            # Verify balance was returned correctly
            assert balance['trx_balance'] == 500.0
            assert balance['network'] == 'shasta'

