"""
Tests for WalletUser model and API endpoints
"""
import pytest
from sqlalchemy import select

from db.models import WalletUser
from services.wallet_user import WalletUserService
from core.utils import get_user_did


class TestWalletUserDIDGeneration:
    """Test automatic DID generation for WalletUser"""
    
    @pytest.mark.asyncio
    async def test_create_user_tron_did_auto_generated(self, test_db):
        """Test that DID is automatically generated for TRON user"""
        wallet_address = "TTestWallet123456789012345678901"
        blockchain = "tron"
        
        # Create user directly via model
        user = WalletUser(
            wallet_address=wallet_address,
            blockchain=blockchain,
            nickname="test_tron_user"
        )
        
        # DID should be None before insert
        assert user.did is None or user.did == ""
        
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # DID should be automatically generated
        expected_did = get_user_did(wallet_address, blockchain)
        assert user.did == expected_did
        assert user.did == "did:tron:ttestwallet123456789012345678901"
    
    @pytest.mark.asyncio
    async def test_create_user_ethereum_did_auto_generated(self, test_db):
        """Test that DID is automatically generated for Ethereum user"""
        wallet_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        blockchain = "ethereum"
        
        user = WalletUser(
            wallet_address=wallet_address,
            blockchain=blockchain,
            nickname="test_eth_user"
        )
        
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        expected_did = get_user_did(wallet_address, blockchain)
        assert user.did == expected_did
        assert user.did == "did:ethr:0x742d35cc6634c0532925a3b844bc9e7595f0beb"
    
    @pytest.mark.asyncio
    async def test_create_user_via_service_did_auto_generated(self, test_db):
        """Test that DID is automatically generated when using WalletUserService"""
        wallet_address = "TServiceTest123456789012345678"
        blockchain = "tron"
        nickname = "service_test_user"
        
        # Create user via service
        user = await WalletUserService.create_user(
            wallet_address=wallet_address,
            blockchain=blockchain,
            nickname=nickname,
            db=test_db
        )
        
        # Verify DID was auto-generated
        expected_did = get_user_did(wallet_address, blockchain)
        assert user.did == expected_did
        assert user.did is not None
        assert user.did.startswith("did:tron:")
    
    @pytest.mark.asyncio
    async def test_did_is_unique(self, test_db):
        """Test that DID uniqueness constraint works"""
        wallet_address = "TUniqueTest123456789012345678901"
        blockchain = "tron"
        
        # Create first user
        user1 = WalletUser(
            wallet_address=wallet_address,
            blockchain=blockchain,
            nickname="unique_user_1"
        )
        test_db.add(user1)
        await test_db.commit()
        
        # Try to create another user with same wallet (will have same DID)
        user2 = WalletUser(
            wallet_address=wallet_address,  # Same address = same DID
            blockchain=blockchain,
            nickname="unique_user_2"
        )
        test_db.add(user2)
        
        # Should fail due to unique constraint on wallet_address
        # (which indirectly tests DID uniqueness)
        with pytest.raises(Exception):  # IntegrityError
            await test_db.commit()
    
    @pytest.mark.asyncio
    async def test_did_not_null_constraint(self, test_db):
        """Test that DID cannot be null (verified by automatic generation)"""
        wallet_address = "TNotNullTest12345678901234567890"
        blockchain = "tron"
        
        user = WalletUser(
            wallet_address=wallet_address,
            blockchain=blockchain,
            nickname="not_null_test"
        )
        
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Verify DID is not null
        assert user.did is not None
        assert len(user.did) > 0
    
    @pytest.mark.asyncio
    async def test_multiple_users_different_dids(self, test_db):
        """Test that different users get different DIDs"""
        users_data = [
            ("TUser1Address123456789012345678", "tron", "user1"),
            ("TUser2Address123456789012345678", "tron", "user2"),
            ("0x1234567890123456789012345678901234567890", "ethereum", "user3"),
        ]
        
        created_dids = []
        
        for wallet_address, blockchain, nickname in users_data:
            user = WalletUser(
                wallet_address=wallet_address,
                blockchain=blockchain,
                nickname=nickname
            )
            test_db.add(user)
            await test_db.commit()
            await test_db.refresh(user)
            
            # Verify DID is unique
            assert user.did not in created_dids
            created_dids.append(user.did)
        
        # Verify we have 3 different DIDs
        assert len(created_dids) == 3
        assert len(set(created_dids)) == 3  # All unique


class TestWalletUserAPI:
    """Test WalletUser API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_user_endpoint_returns_did(self, admin_client, test_db):
        """Test that creating user via API returns DID"""
        response = await admin_client.post(
            "/api/admin/wallet-users",
            json={
                "wallet_address": "TAPITest12345678901234567890123",
                "blockchain": "tron",
                "nickname": "api_test_user",
                "access_to_admin_panel": False,
                "is_verified": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify DID is in response
        assert "did" in data
        assert data["did"].startswith("did:tron:")
        assert data["wallet_address"].lower() in data["did"]
    
    @pytest.mark.asyncio
    async def test_get_user_endpoint_returns_did(self, admin_client, test_db):
        """Test that getting user via API returns DID"""
        # Create user first
        user = WalletUser(
            wallet_address="TGetTest123456789012345678901234",
            blockchain="tron",
            nickname="get_test_user"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Get user via API
        response = await admin_client.get(f"/api/admin/wallet-users/{user.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify DID is in response
        assert "did" in data
        assert data["did"] == user.did
    
    @pytest.mark.asyncio
    async def test_list_users_endpoint_returns_did(self, admin_client, test_db):
        """Test that listing users via API returns DID"""
        # Create a user
        user = WalletUser(
            wallet_address="TListTest123456789012345678901234",
            blockchain="tron",
            nickname="list_test_user"
        )
        test_db.add(user)
        await test_db.commit()
        
        # List users via API
        response = await admin_client.get("/api/admin/wallet-users")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify DID is in each user
        assert len(data["users"]) > 0
        for user_data in data["users"]:
            assert "did" in user_data
            assert user_data["did"].startswith("did:")
    
    @pytest.mark.asyncio
    async def test_get_profile_by_user_id(self, test_client, test_db):
        """Test getting user profile by user_id via public endpoint"""
        # Create a user
        user = WalletUser(
            wallet_address="TProfileTest1234567890123456789",
            blockchain="tron",
            nickname="profile_test_user"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Get profile by user_id
        response = await test_client.get(f"/api/profile/user/{user.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response contains correct data
        assert data["wallet_address"] == user.wallet_address
        assert data["blockchain"] == user.blockchain
        assert data["did"] == user.did
        assert data["nickname"] == user.nickname
        assert "created_at" in data
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_get_profile_by_did(self, test_client, test_db):
        """Test getting user profile by DID via public endpoint"""
        # Create a user
        user = WalletUser(
            wallet_address="TDIDProfileTest123456789012345",
            blockchain="tron",
            nickname="did_profile_test_user"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Get profile by DID
        response = await test_client.get(f"/api/profile/user/{user.did}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response contains correct data
        assert data["wallet_address"] == user.wallet_address
        assert data["blockchain"] == user.blockchain
        assert data["did"] == user.did
        assert data["nickname"] == user.nickname
        assert data["did"].startswith("did:tron:")
    
    @pytest.mark.asyncio
    async def test_get_profile_by_invalid_identifier(self, test_client, test_db):
        """Test getting user profile with invalid identifier"""
        # Try with invalid identifier (not a number, not a DID)
        response = await test_client.get("/api/profile/user/invalid_identifier")
        
        assert response.status_code == 400
        assert "Invalid identifier" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, test_client, test_db):
        """Test getting profile for non-existent user"""
        # Try with non-existent user_id
        response = await test_client.get("/api/profile/user/99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        
        # Try with non-existent DID
        response = await test_client.get("/api/profile/user/did:tron:nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

