"""
Tests for Connection protocol handler (RFC 0160)
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from cryptography.hazmat.primitives.asymmetric import ec
from didcomm.crypto import EthKeyPair, KeyPair
from didcomm.message import DIDCommMessage, pack_message, unpack_message
from services.protocols.connection import ConnectionHandler
import db


# In-memory storage for tests to replace database
_test_connections = {}


class MockConnection:
    """Mock Connection model for tests"""
    def __init__(self, connection_id, my_did, their_did, status, connection_type, 
                 label, connection_metadata, message_data, established_at=None):
        self.connection_id = connection_id
        self.my_did = my_did
        self.their_did = their_did
        self.status = status
        self.connection_type = connection_type
        self.label = label
        self.connection_metadata = connection_metadata
        self.message_data = message_data
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.established_at = established_at


@pytest.fixture(scope="session", autouse=True)
def mock_db_session_local():
    """Mock SessionLocal to be initialized for all tests"""
    # Store original value
    original_session_local = db.SessionLocal
    # Set mock
    db.SessionLocal = Mock()
    yield
    # Restore
    db.SessionLocal = original_session_local


@pytest.fixture(autouse=True)
def mock_db():
    """Mock database for all connection tests"""
    global _test_connections
    _test_connections = {}
    
    # Patch ConnectionHandler methods to use in-memory storage
    original_save = ConnectionHandler._save_connection
    original_get_by_id = ConnectionHandler._get_connection_by_id
    original_get_by_did = ConnectionHandler._get_connection_by_their_did
    original_get_pending = ConnectionHandler._get_pending_connections
    original_get_established = ConnectionHandler._get_established_connections
    
    async def mock_save(self, connection_id, status, connection_type, their_did=None, 
                       label=None, metadata=None, message_data=None):
        key = f"{self.my_did}:{connection_id}"
        conn = MockConnection(
            connection_id, self.my_did, their_did, status, connection_type,
            label, metadata, message_data,
            datetime.now(timezone.utc) if status == 'established' else None
        )
        _test_connections[key] = conn
        return conn
    
    async def mock_get_by_id(self, connection_id):
        key = f"{self.my_did}:{connection_id}"
        return _test_connections.get(key)
    
    async def mock_get_by_did(self, their_did):
        for conn in _test_connections.values():
            if conn.my_did == self.my_did and conn.their_did == their_did and conn.status == 'established':
                return conn
        return None
    
    async def mock_get_pending(self):
        return [conn for conn in _test_connections.values() 
                if conn.my_did == self.my_did and conn.status == 'pending']
    
    async def mock_get_established(self):
        return [conn for conn in _test_connections.values() 
                if conn.my_did == self.my_did and conn.status == 'established']
    
    ConnectionHandler._save_connection = mock_save
    ConnectionHandler._get_connection_by_id = mock_get_by_id
    ConnectionHandler._get_connection_by_their_did = mock_get_by_did
    ConnectionHandler._get_pending_connections = mock_get_pending
    ConnectionHandler._get_established_connections = mock_get_established
    
    yield
    
    # Restore original methods
    ConnectionHandler._save_connection = original_save
    ConnectionHandler._get_connection_by_id = original_get_by_id
    ConnectionHandler._get_connection_by_their_did = original_get_by_did
    ConnectionHandler._get_pending_connections = original_get_pending
    ConnectionHandler._get_established_connections = original_get_established
    
    _test_connections = {}


class TestConnectionHandlerEth:
    """Test Connection protocol with Ethereum keys"""
    
    @pytest.fixture
    def alice_key(self):
        """Alice's Ethereum key pair"""
        return EthKeyPair()
    
    @pytest.fixture
    def bob_key(self):
        """Bob's Ethereum key pair"""
        return EthKeyPair()
    
    @pytest.fixture
    def alice_handler(self, alice_key, mock_db_session_local):
        """Alice's connection handler"""
        alice_did = f"did:ethr:{alice_key.address}"
        return ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
    
    @pytest.fixture
    def bob_handler(self, bob_key, mock_db_session_local):
        """Bob's connection handler"""
        bob_did = f"did:ethr:{bob_key.address}"
        return ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
    
    @pytest.mark.asyncio
    async def test_create_invitation(self, alice_handler):
        """Test creating a connection invitation"""
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did],
            routing_keys=[],
            image_url="https://alice.example.com/avatar.png"
        )
        
        assert invitation.type == ConnectionHandler.MSG_TYPE_INVITATION
        assert invitation.body["label"] == "Alice Agent"
        assert alice_handler.my_did in invitation.body["recipient_keys"]
        assert invitation.body["service_endpoint"] == "https://alice.example.com/didcomm"
        assert invitation.body["image_url"] == "https://alice.example.com/avatar.png"
        
        # Verify invitation is stored as pending
        pending = await alice_handler.list_pending_connections()
        assert any(p["connection_id"] == invitation.id for p in pending)
    
    @pytest.mark.asyncio
    async def test_validate_invitation(self, alice_handler):
        """Test invitation validation"""
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        assert alice_handler.validate_invitation(invitation) is True
        
        # Test invalid invitation (missing label)
        invalid_invitation = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_INVITATION,
            body={"recipient_keys": [alice_handler.my_did]}
        )
        assert alice_handler.validate_invitation(invalid_invitation) is False
        
        # Test invalid invitation (missing recipient_keys)
        invalid_invitation2 = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_INVITATION,
            body={"label": "Test"}
        )
        assert alice_handler.validate_invitation(invalid_invitation2) is False
    
    @pytest.mark.asyncio
    async def test_create_request(self, alice_handler, bob_handler):
        """Test creating a connection request in response to invitation"""
        # Alice creates invitation
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        # Bob creates request
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent",
            image_url="https://bob.example.com/avatar.png"
        )
        
        assert request.type == ConnectionHandler.MSG_TYPE_REQUEST
        assert request.body["label"] == "Bob Agent"
        assert request.body["connection"]["DID"] == bob_handler.my_did
        assert "DIDDoc" in request.body["connection"]
        assert request.body["image_url"] == "https://bob.example.com/avatar.png"
        
        # Verify request is stored as pending
        pending = await bob_handler.list_pending_connections()
        assert any(p["connection_id"] == request.id for p in pending)
    
    @pytest.mark.asyncio
    async def test_validate_request(self, alice_handler, bob_handler):
        """Test request validation"""
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent"
        )
        
        assert bob_handler.validate_request(request) is True
        
        # Test invalid request (missing label)
        invalid_request = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_REQUEST,
            body={"connection": {"DID": bob_handler.my_did}}
        )
        assert bob_handler.validate_request(invalid_request) is False
        
        # Test invalid request (missing connection)
        invalid_request2 = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_REQUEST,
            body={"label": "Test"}
        )
        assert bob_handler.validate_request(invalid_request2) is False
    
    @pytest.mark.asyncio
    async def test_handle_request_creates_response(self, alice_handler, bob_handler):
        """Test that handling a request creates an appropriate response"""
        # Alice creates invitation
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        # Bob creates request
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent"
        )
        
        # Alice handles the request
        response = await alice_handler.handle_message(request)
        
        assert response is not None
        assert response.type == ConnectionHandler.MSG_TYPE_RESPONSE
        assert response.thid == request.id
        assert response.body["connection"]["DID"] == alice_handler.my_did
        
        # Verify connection is established for Alice
        alice_connections = await alice_handler.list_connections()
        assert any(c["did"] == bob_handler.my_did for c in alice_connections)
    
    @pytest.mark.asyncio
    async def test_validate_response(self, alice_handler, bob_handler):
        """Test response validation"""
        # Create a valid response
        response = alice_handler.create_response(
            request_id=str(uuid.uuid4()),
            requester_did=bob_handler.my_did
        )
        
        assert alice_handler.validate_response(response) is True
        
        # Test invalid response (missing thid)
        invalid_response = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_RESPONSE,
            body={"connection": {"DID": alice_handler.my_did}}
        )
        assert alice_handler.validate_response(invalid_response) is False
        
        # Test invalid response (missing connection)
        invalid_response2 = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_RESPONSE,
            body={},
            thid=str(uuid.uuid4())
        )
        assert alice_handler.validate_response(invalid_response2) is False
    
    @pytest.mark.asyncio
    async def test_handle_response_establishes_connection(self, alice_handler, bob_handler):
        """Test that handling a response establishes the connection"""
        # Alice creates invitation
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        # Bob creates request
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent"
        )
        
        # Alice handles request and creates response
        response = await alice_handler.handle_message(request)
        
        # Bob handles the response
        result = await bob_handler.handle_message(response)
        
        assert result is None  # No further response needed
        
        # Verify connection is established for Bob
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == alice_handler.my_did for c in bob_connections)
    
    @pytest.mark.asyncio
    async def test_full_connection_flow(self, alice_handler, bob_handler):
        """Test complete connection establishment flow"""
        # Step 1: Alice creates invitation
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        assert alice_handler.validate_invitation(invitation)
        
        # Step 2: Bob receives invitation and creates request
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent"
        )
        
        assert bob_handler.validate_request(request)
        
        # Step 3: Alice receives request and creates response
        response = await alice_handler.handle_message(request)
        
        assert response is not None
        assert alice_handler.validate_response(response)
        
        # Check Alice's established connections
        alice_connections = await alice_handler.list_connections()
        assert any(c["did"] == bob_handler.my_did for c in alice_connections)
        
        # Step 4: Bob receives response and completes connection
        result = await bob_handler.handle_message(response)
        
        assert result is None
        
        # Check Bob's established connections
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == alice_handler.my_did for c in bob_connections)
        
        # Verify both sides have the connection established
        alice_conn = await alice_handler.get_connection(bob_handler.my_did)
        bob_conn = await bob_handler.get_connection(alice_handler.my_did)
        
        assert alice_conn is not None
        assert bob_conn is not None
        assert alice_conn["did"] == bob_handler.my_did
        assert bob_conn["did"] == alice_handler.my_did
    
    @pytest.mark.asyncio
    async def test_list_connections(self, alice_handler, bob_handler):
        """Test listing established connections"""
        # Initially no connections
        assert len(await alice_handler.list_connections()) == 0
        assert len(await bob_handler.list_connections()) == 0
        
        # Establish connection
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        request = await bob_handler.create_request(invitation=invitation, label="Bob Agent")
        response = await alice_handler.handle_message(request)
        await bob_handler.handle_message(response)
        
        # Now both should have one connection
        assert len(await alice_handler.list_connections()) == 1
        assert len(await bob_handler.list_connections()) == 1
    
    @pytest.mark.asyncio
    async def test_list_pending_connections(self, alice_handler):
        """Test listing pending connections"""
        # Create invitation (pending)
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        pending = await alice_handler.list_pending_connections()
        assert len(pending) == 1
        assert pending[0]["type"] == "invitation"
    
    @pytest.mark.asyncio
    async def test_encrypted_connection_flow(self, alice_handler, bob_handler, alice_key, bob_key):
        """Test connection flow with encrypted messages"""
        # Step 1: Alice creates invitation
        invitation = await alice_handler.create_invitation(
            label="Alice Agent",
            recipient_keys=[alice_handler.my_did]
        )
        
        # Step 2: Bob creates and packs request
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent"
        )
        
        # Pack the request with encryption
        packed_request = pack_message(
            request,
            bob_key,
            [alice_key.public_key],
            encrypt=True
        )
        
        # Alice unpacks and handles request
        unpacked_request = unpack_message(
            packed_request,
            alice_key,
            sender_public_key=bob_key.public_key,
            sender_key_type="ETH"
        )
        
        response = await alice_handler.handle_message(unpacked_request)
        
        # Pack the response with encryption
        packed_response = pack_message(
            response,
            alice_key,
            [bob_key.public_key],
            encrypt=True
        )
        
        # Bob unpacks and handles response
        unpacked_response = unpack_message(
            packed_response,
            bob_key,
            sender_public_key=alice_key.public_key,
            sender_key_type="ETH"
        )
        
        await bob_handler.handle_message(unpacked_response)
        
        # Verify connection established
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_handler.my_did for c in alice_connections)
        assert any(c["did"] == alice_handler.my_did for c in bob_connections)
    
    @pytest.mark.asyncio
    async def test_unsupported_message_type(self, alice_handler):
        """Test handling of unsupported message types"""
        invalid_message = DIDCommMessage(
            id=str(uuid.uuid4()),
            type="https://didcomm.org/connections/1.0/unknown",
            body={}
        )
        
        with pytest.raises(ValueError, match="Unsupported message type"):
            await alice_handler.handle_message(invalid_message)
    
    @pytest.mark.asyncio
    async def test_protocol_name_and_version(self, alice_handler):
        """Test protocol name and version support"""
        assert alice_handler.protocol_name == "connections"
        assert "1.0" in alice_handler.supported_versions
        
        # Test message type support
        assert alice_handler.supports_message_type(
            "https://didcomm.org/connections/1.0/invitation"
        )
        assert alice_handler.supports_message_type(
            "https://didcomm.org/connections/1.0/request"
        )
        assert alice_handler.supports_message_type(
            "https://didcomm.org/connections/1.0/response"
        )
        assert not alice_handler.supports_message_type(
            "https://didcomm.org/trust-ping/1.0/ping"
        )


class TestConnectionHandlerRSA:
    """Test Connection protocol with RSA keys"""
    
    @pytest.fixture
    def alice_key(self):
        """Alice's RSA key pair"""
        return KeyPair.generate_rsa(key_size=2048)
    
    @pytest.fixture
    def bob_key(self):
        """Bob's RSA key pair"""
        return KeyPair.generate_rsa(key_size=2048)
    
    @pytest.fixture
    def alice_handler(self, alice_key):
        """Alice's connection handler"""
        alice_did = f"did:key:rsa:{alice_key.to_pem()[:20].hex()}"
        return ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
    
    @pytest.fixture
    def bob_handler(self, bob_key):
        """Bob's connection handler"""
        bob_did = f"did:key:rsa:{bob_key.to_pem()[:20].hex()}"
        return ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
    
    @pytest.mark.asyncio
    async def test_full_connection_flow_rsa(self, alice_handler, bob_handler):
        """Test complete connection flow with RSA keys"""
        # Complete flow
        invitation = await alice_handler.create_invitation(
            label="Alice Agent (RSA)",
            recipient_keys=[alice_handler.my_did]
        )
        
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent (RSA)"
        )
        
        response = await alice_handler.handle_message(request)
        await bob_handler.handle_message(response)
        
        # Verify connections
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_handler.my_did for c in alice_connections)
        assert any(c["did"] == alice_handler.my_did for c in bob_connections)


class TestConnectionHandlerEC:
    """Test Connection protocol with Elliptic Curve keys"""
    
    @pytest.fixture
    def alice_key(self):
        """Alice's EC key pair"""
        return KeyPair.generate_ec(curve=ec.SECP256K1())
    
    @pytest.fixture
    def bob_key(self):
        """Bob's EC key pair"""
        return KeyPair.generate_ec(curve=ec.SECP256K1())
    
    @pytest.fixture
    def alice_handler(self, alice_key):
        """Alice's connection handler"""
        alice_did = f"did:key:ec:alice-{uuid.uuid4().hex[:8]}"
        return ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
    
    @pytest.fixture
    def bob_handler(self, bob_key):
        """Bob's connection handler"""
        bob_did = f"did:key:ec:bob-{uuid.uuid4().hex[:8]}"
        return ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
    
    @pytest.mark.asyncio
    async def test_full_connection_flow_ec(self, alice_handler, bob_handler):
        """Test complete connection flow with EC keys"""
        # Complete flow
        invitation = await alice_handler.create_invitation(
            label="Alice Agent (EC)",
            recipient_keys=[alice_handler.my_did]
        )
        
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent (EC)"
        )
        
        response = await alice_handler.handle_message(request)
        await bob_handler.handle_message(response)
        
        # Verify connections
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_handler.my_did for c in alice_connections)
        assert any(c["did"] == alice_handler.my_did for c in bob_connections)


class TestConnectionHandlerEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def handler(self):
        """Basic handler for edge case testing"""
        key = EthKeyPair()
        did = f"did:ethr:{key.address}"
        return ConnectionHandler(key, did)
    
    @pytest.mark.asyncio
    async def test_request_without_did(self, handler):
        """Test handling request without DID in connection"""
        invalid_request = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_REQUEST,
            body={
                "label": "Test",
                "connection": {}  # Missing DID
            }
        )
        
        with pytest.raises(ValueError, match="missing DID"):
            await handler.handle_message(invalid_request)
    
    @pytest.mark.asyncio
    async def test_response_without_did(self, handler):
        """Test handling response without DID in connection"""
        invalid_response = DIDCommMessage(
            id=str(uuid.uuid4()),
            type=ConnectionHandler.MSG_TYPE_RESPONSE,
            body={
                "connection": {}  # Missing DID
            },
            thid=str(uuid.uuid4())
        )
        
        with pytest.raises(ValueError, match="missing DID"):
            await handler.handle_message(invalid_response)
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_connection(self, handler):
        """Test getting a connection that doesn't exist"""
        result = await handler.get_connection("did:example:nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_custom_did_doc(self, handler):
        """Test creating request with custom DID document"""
        invitation = await handler.create_invitation(
            label="Test Agent",
            recipient_keys=[handler.my_did]
        )
        
        custom_did_doc = {
            "@context": "https://w3id.org/did/v1",
            "id": handler.my_did,
            "custom_field": "custom_value"
        }
        
        request = await handler.create_request(
            invitation=invitation,
            label="Custom Agent",
            did_doc=custom_did_doc
        )
        
        assert request.body["connection"]["DIDDoc"]["custom_field"] == "custom_value"
    
    @pytest.mark.asyncio
    async def test_eth_to_rsa_connection_flow(self):
        """Test connection flow between Ethereum and RSA key holders"""
        # Alice uses Ethereum keys
        alice_key = EthKeyPair()
        alice_did = f"did:ethr:{alice_key.address}"
        alice_handler = ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
        
        # Bob uses RSA keys
        bob_key = KeyPair.generate_rsa(key_size=2048)
        bob_did = f"did:key:rsa:{bob_key.to_pem()[:20].hex()}"
        bob_handler = ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
        
        # Full connection flow
        invitation = await alice_handler.create_invitation(
            label="Alice Agent (ETH)",
            recipient_keys=[alice_did]
        )
        
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent (RSA)"
        )
        
        response = await alice_handler.handle_message(request)
        await bob_handler.handle_message(response)
        
        # Verify connection established despite different key types
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_did for c in alice_connections)
        assert any(c["did"] == alice_did for c in bob_connections)
        
        alice_conn = await alice_handler.get_connection(bob_did)
        bob_conn = await bob_handler.get_connection(alice_did)
        
        assert alice_conn["label"] == "Bob Agent (RSA)"
        assert bob_conn["label"] == "Alice Agent (ETH)"
    
    @pytest.mark.asyncio
    async def test_rsa_to_eth_connection_flow(self):
        """Test connection flow between RSA and Ethereum key holders"""
        # Alice uses RSA keys
        alice_key = KeyPair.generate_rsa(key_size=2048)
        alice_did = f"did:key:rsa:{alice_key.to_pem()[:20].hex()}"
        alice_handler = ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
        
        # Bob uses Ethereum keys
        bob_key = EthKeyPair()
        bob_did = f"did:ethr:{bob_key.address}"
        bob_handler = ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
        
        # Full connection flow
        invitation = await alice_handler.create_invitation(
            label="Alice Agent (RSA)",
            recipient_keys=[alice_did]
        )
        
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent (ETH)"
        )
        
        response = await alice_handler.handle_message(request)
        await bob_handler.handle_message(response)
        
        # Verify connection established despite different key types
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_did for c in alice_connections)
        assert any(c["did"] == alice_did for c in bob_connections)
    
    @pytest.mark.asyncio
    async def test_eth_to_ec_connection_flow(self):
        """Test connection flow between Ethereum and EC key holders"""
        # Alice uses Ethereum keys (which is secp256k1 EC)
        alice_key = EthKeyPair()
        alice_did = f"did:ethr:{alice_key.address}"
        alice_handler = ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
        
        # Bob uses EC keys with secp256r1 (P-256) curve
        bob_key = KeyPair.generate_ec(curve=ec.SECP256R1())
        bob_did = f"did:key:ec:bob-{uuid.uuid4().hex[:8]}"
        bob_handler = ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
        
        # Full connection flow
        invitation = await alice_handler.create_invitation(
            label="Alice Agent (ETH/secp256k1)",
            recipient_keys=[alice_did]
        )
        
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent (EC/secp256r1)"
        )
        
        response = await alice_handler.handle_message(request)
        await bob_handler.handle_message(response)
        
        # Verify connection established despite different curves
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_did for c in alice_connections)
        assert any(c["did"] == alice_did for c in bob_connections)
    
    @pytest.mark.asyncio
    async def test_rsa_to_ec_connection_flow(self):
        """Test connection flow between RSA and EC key holders"""
        # Alice uses RSA keys
        alice_key = KeyPair.generate_rsa(key_size=2048)
        alice_did = f"did:key:rsa:{alice_key.to_pem()[:20].hex()}"
        alice_handler = ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
        
        # Bob uses EC keys
        bob_key = KeyPair.generate_ec(curve=ec.SECP256K1())
        bob_did = f"did:key:ec:bob-{uuid.uuid4().hex[:8]}"
        bob_handler = ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
        
        # Full connection flow
        invitation = await alice_handler.create_invitation(
            label="Alice Agent (RSA)",
            recipient_keys=[alice_did]
        )
        
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent (EC)"
        )
        
        response = await alice_handler.handle_message(request)
        await bob_handler.handle_message(response)
        
        # Verify connection established despite different key types
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_did for c in alice_connections)
        assert any(c["did"] == alice_did for c in bob_connections)
    
    @pytest.mark.asyncio
    async def test_mixed_crypto_with_encryption(self):
        """Test encrypted connection flow with mixed cryptography (ETH + RSA)"""
        # Alice uses Ethereum keys
        alice_key = EthKeyPair()
        alice_did = f"did:ethr:{alice_key.address}"
        alice_handler = ConnectionHandler(
            alice_key,
            alice_did,
            service_endpoint="https://alice.example.com/didcomm"
        )
        
        # Bob uses RSA keys
        bob_key = KeyPair.generate_rsa(key_size=2048)
        bob_did = f"did:key:rsa:{bob_key.to_pem()[:20].hex()}"
        bob_handler = ConnectionHandler(
            bob_key,
            bob_did,
            service_endpoint="https://bob.example.com/didcomm"
        )
        
        # Create invitation
        invitation = await alice_handler.create_invitation(
            label="Alice Agent (ETH)",
            recipient_keys=[alice_did]
        )
        
        # Bob creates and packs request with encryption
        request = await bob_handler.create_request(
            invitation=invitation,
            label="Bob Agent (RSA)"
        )
        
        packed_request = pack_message(
            request,
            bob_key,
            [alice_key.public_key],
            encrypt=True
        )
        
        # Alice unpacks and handles request
        unpacked_request = unpack_message(
            packed_request,
            alice_key,
            sender_public_key=bob_key.public_key,
            sender_key_type="RSA"
        )
        
        response = await alice_handler.handle_message(unpacked_request)
        
        # Pack response with encryption
        packed_response = pack_message(
            response,
            alice_key,
            [bob_key.public_key],
            encrypt=True
        )
        
        # Bob unpacks and handles response
        unpacked_response = unpack_message(
            packed_response,
            bob_key,
            sender_public_key=alice_key.public_key,
            sender_key_type="ETH"
        )
        
        await bob_handler.handle_message(unpacked_response)
        
        # Verify encrypted connection established with mixed crypto
        alice_connections = await alice_handler.list_connections()
        bob_connections = await bob_handler.list_connections()
        assert any(c["did"] == bob_did for c in alice_connections)
        assert any(c["did"] == alice_did for c in bob_connections)

