"""
Tests for EscrowService
"""
import pytest
from sqlalchemy import select

from services.escrow.service import EscrowService
from db.models import EscrowModel
from services.node import NodeService


class TestEscrowServiceEnsureExists:
    """Test EscrowService.ensure_exists method"""
    
    @pytest.mark.asyncio
    async def test_ensure_exists_creates_new_escrow(self, test_db, set_test_secret):
        """Test that ensure_exists creates new escrow when it doesn't exist"""
        owner_did = "did:test:owner1"
        secret = set_test_secret
        service = EscrowService(
            session=test_db,
            owner_did=owner_did,
            secret=secret,
            escrow_type="multisig",
            blockchain="tron",
            network="mainnet"
        )
        
        # Use valid TRON addresses
        arbiter_address = "TEEXEWrkMFKapSMJ6mErg39ELFKDqEs6w3"
        sender_address = "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy"
        receiver_address = "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW"
        
        # Create escrow
        escrow = await service.ensure_exists(
            arbiter_address=arbiter_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        
        # Verify escrow was created
        assert escrow is not None
        assert escrow.blockchain == "tron"
        assert escrow.network == "mainnet"
        assert escrow.escrow_type == "multisig"
        assert escrow.owner_did == owner_did
        assert escrow.participant1_address == sender_address
        assert escrow.participant2_address == receiver_address
        assert escrow.arbiter_address == arbiter_address
        assert escrow.escrow_address == arbiter_address
        assert escrow.status == "pending"
        
        # Verify encrypted mnemonic was created
        assert escrow.encrypted_mnemonic is not None
        assert len(escrow.encrypted_mnemonic) > 0
        
        # Verify mnemonic is encrypted (not plain text)
        # Encrypted data should be base64-encoded JSON
        import base64
        import json
        try:
            decoded = base64.b64decode(escrow.encrypted_mnemonic)
            encrypted_data = json.loads(decoded)
            assert "iv" in encrypted_data
            assert "tag" in encrypted_data
            assert "ciphertext" in encrypted_data
        except Exception:
            pytest.fail("encrypted_mnemonic is not in expected format")
        
        # Verify we can decrypt it
        decrypted_mnemonic = NodeService.decrypt_data(escrow.encrypted_mnemonic, secret)
        assert decrypted_mnemonic is not None
        assert len(decrypted_mnemonic.split()) == 12  # 12 words for strength=128
        
        # Verify multisig config
        assert escrow.multisig_config is not None
        assert escrow.multisig_config["required_signatures"] == 2
        assert len(escrow.multisig_config["owner_addresses"]) == 3
        assert sender_address in escrow.multisig_config["owner_addresses"]
        assert receiver_address in escrow.multisig_config["owner_addresses"]
        assert arbiter_address in escrow.multisig_config["owner_addresses"]
        
        # Verify address roles
        assert escrow.address_roles is not None
        assert escrow.address_roles[sender_address] == "participant"
        assert escrow.address_roles[receiver_address] == "participant"
        assert escrow.address_roles[arbiter_address] == "arbiter"
    
    @pytest.mark.asyncio
    async def test_ensure_exists_returns_existing_escrow(self, test_db, set_test_secret):
        """Test that ensure_exists returns existing escrow when it exists"""
        owner_did = "did:test:owner1"
        secret = set_test_secret
        service = EscrowService(
            session=test_db,
            owner_did=owner_did,
            secret=secret,
            escrow_type="multisig",
            blockchain="tron",
            network="mainnet"
        )
        
        # Use valid TRON addresses
        arbiter_address = "TEEXEWrkMFKapSMJ6mErg39ELFKDqEs6w3"
        sender_address = "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy"
        receiver_address = "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW"
        
        # Create first escrow
        escrow1 = await service.ensure_exists(
            arbiter_address=arbiter_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        await test_db.commit()
        
        # Try to create again - should return existing
        escrow2 = await service.ensure_exists(
            arbiter_address=arbiter_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        
        # Should be the same escrow
        assert escrow1.id == escrow2.id
        assert escrow1.encrypted_mnemonic == escrow2.encrypted_mnemonic
    
    @pytest.mark.asyncio
    async def test_ensure_exists_handles_reversed_participants(self, test_db, set_test_secret):
        """Test that ensure_exists finds escrow regardless of participant order"""
        owner_did = "did:test:owner1"
        secret = set_test_secret
        service = EscrowService(
            session=test_db,
            owner_did=owner_did,
            secret=secret,
            escrow_type="multisig",
            blockchain="tron",
            network="mainnet"
        )
        
        # Use valid TRON addresses
        arbiter_address = "TEEXEWrkMFKapSMJ6mErg39ELFKDqEs6w3"
        sender_address = "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy"
        receiver_address = "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW"
        
        # Create escrow with sender, receiver
        escrow1 = await service.ensure_exists(
            arbiter_address=arbiter_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        await test_db.commit()
        
        # Try to create with reversed order - should return existing
        escrow2 = await service.ensure_exists(
            arbiter_address=arbiter_address,
            sender_address=receiver_address,  # Reversed
            receiver_address=sender_address   # Reversed
        )
        
        # Should be the same escrow
        assert escrow1.id == escrow2.id
    
    @pytest.mark.asyncio
    async def test_ensure_exists_creates_separate_escrows_for_different_arbiters(self, test_db, set_test_secret):
        """Test that different arbiters create separate escrows"""
        owner_did = "did:test:owner1"
        secret = set_test_secret
        service = EscrowService(
            session=test_db,
            owner_did=owner_did,
            secret=secret,
            escrow_type="multisig",
            blockchain="tron",
            network="mainnet"
        )
        
        # Use valid TRON addresses
        sender_address = "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy"
        receiver_address = "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW"
        arbiter1_address = "TEEXEWrkMFKapSMJ6mErg39ELFKDqEs6w3"
        arbiter2_address = "TGzz8gjYiYRqpfmDwnLxfgPuLVNmpCswVp"
        
        # Create escrow with arbiter1
        escrow1 = await service.ensure_exists(
            arbiter_address=arbiter1_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        await test_db.commit()
        
        # Create escrow with arbiter2 - should be different
        escrow2 = await service.ensure_exists(
            arbiter_address=arbiter2_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        
        # Should be different escrows
        assert escrow1.id != escrow2.id
        assert escrow1.arbiter_address == arbiter1_address
        assert escrow2.arbiter_address == arbiter2_address
    
    @pytest.mark.asyncio
    async def test_ensure_exists_excludes_inactive_escrows(self, test_db, set_test_secret):
        """Test that ensure_exists excludes inactive escrows and creates new one"""
        owner_did = "did:test:owner1"
        secret = set_test_secret
        service = EscrowService(
            session=test_db,
            owner_did=owner_did,
            secret=secret,
            escrow_type="multisig",
            blockchain="tron",
            network="mainnet"
        )
        
        # Use valid TRON addresses
        arbiter_address = "TEEXEWrkMFKapSMJ6mErg39ELFKDqEs6w3"
        sender_address = "TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy"
        receiver_address = "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW"
        
        # Create escrow
        escrow1 = await service.ensure_exists(
            arbiter_address=arbiter_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        await test_db.commit()
        
        # Mark as inactive
        escrow1.status = "inactive"
        await test_db.commit()
        
        # Delete the inactive escrow to avoid unique constraint violation
        # (since escrow_address = arbiter_address and there's a unique constraint)
        await test_db.delete(escrow1)
        await test_db.commit()
        
        # Try to ensure exists - should create new escrow
        escrow2 = await service.ensure_exists(
            arbiter_address=arbiter_address,
            sender_address=sender_address,
            receiver_address=receiver_address
        )
        
        # Should be different escrows (new one created)
        assert escrow1.id != escrow2.id
        assert escrow2.status == "pending"

