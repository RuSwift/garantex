# Aries Protocol Handlers

This module provides implementations of various Aries RFC protocols for DIDComm messaging. Each protocol is implemented as a handler class that inherits from the base `ProtocolHandler` class.

## Supported Protocols

### 1. Trust Ping Protocol (RFC 0048)

**Module:** `trust_ping.py`  
**Protocol Name:** `trust-ping`  
**Versions:** 1.0  
**Reference:** https://github.com/hyperledger/aries-rfcs/tree/main/features/0048-trust-ping

The Trust Ping protocol is used to test connectivity and responsiveness between DIDComm agents. It's a simple ping-pong protocol where one agent sends a ping and optionally requests a response.

**Message Types:**
- `https://didcomm.org/trust-ping/1.0/ping` - Ping message
- `https://didcomm.org/trust-ping/1.0/ping-response` - Pong response

**Example Usage:**
```python
from didcomm.crypto import EthKeyPair
from services.protocols import TrustPingHandler

# Initialize handler
my_key = EthKeyPair()
my_did = f"did:ethr:{my_key.address}"
handler = TrustPingHandler(my_key, my_did)

# Create a ping
ping = handler.create_ping(
    recipient_did="did:example:recipient",
    response_requested=True,
    comment="Are you there?"
)

# Handle incoming ping
response = await handler.handle_message(ping)
```

### 2. Connection Protocol (RFC 0160)

**Module:** `connection.py`  
**Protocol Name:** `connections`  
**Versions:** 1.0  
**Reference:** https://github.com/decentralized-identity/aries-rfcs/tree/main/features/0160-connection-protocol

The Connection protocol is used to establish a connection between two DIDComm agents. It involves three main steps:
1. **Invitation** - One party creates and shares an invitation
2. **Request** - The other party responds with a connection request
3. **Response** - The inviter accepts the connection with a response

After these steps, both parties have a mutual connection for future communication.

**Message Types:**
- `https://didcomm.org/connections/1.0/invitation` - Connection invitation
- `https://didcomm.org/connections/1.0/request` - Connection request
- `https://didcomm.org/connections/1.0/response` - Connection response

**Example Usage:**

```python
from didcomm.crypto import EthKeyPair
from services.protocols import ConnectionHandler

# Alice creates an invitation
alice_key = EthKeyPair()
alice_did = f"did:ethr:{alice_key.address}"
alice_handler = ConnectionHandler(
    alice_key,
    alice_did,
    service_endpoint="https://alice.example.com/didcomm"
)

invitation = alice_handler.create_invitation(
    label="Alice Agent",
    recipient_keys=[alice_did]
)

# Bob receives invitation and creates request
bob_key = EthKeyPair()
bob_did = f"did:ethr:{bob_key.address}"
bob_handler = ConnectionHandler(
    bob_key,
    bob_did,
    service_endpoint="https://bob.example.com/didcomm"
)

request = bob_handler.create_request(
    invitation=invitation,
    label="Bob Agent"
)

# Alice handles request and creates response
response = await alice_handler.handle_message(request)

# Bob handles response and completes connection
await bob_handler.handle_message(response)

# Now both parties have an established connection
alice_conn = alice_handler.get_connection(bob_did)
bob_conn = bob_handler.get_connection(alice_did)
```

**Connection Management:**
```python
# List all established connections
connections = handler.list_connections()

# List pending connections (invitations and requests)
pending = handler.list_pending_connections()

# Get specific connection by DID
connection = handler.get_connection("did:example:recipient")
```

## Architecture

### Base Protocol Handler

All protocol handlers inherit from the `ProtocolHandler` base class which provides:

- **Message Type Validation:** Validates incoming message types against supported protocols
- **Message Packing/Unpacking:** Handles encryption and decryption of DIDComm messages
- **Protocol Routing:** Routes messages to appropriate handler methods
- **Utility Methods:** Common functionality for protocol version extraction, validation, etc.

### Protocol Registry

The `PROTOCOL_HANDLERS` dictionary in `__init__.py` maintains a registry of all available protocol handlers:

```python
PROTOCOL_HANDLERS = {
    "trust-ping": TrustPingHandler,
    "connections": ConnectionHandler,
}
```

Use the `get_protocol_handler()` function to retrieve a handler class by protocol name:

```python
from services.protocols import get_protocol_handler

handler_class = get_protocol_handler("connections")
if handler_class:
    handler = handler_class(my_key, my_did)
```

## Cryptographic Key Support

All protocol handlers support multiple cryptographic key types:

- **Ethereum Keys** (`EthKeyPair`) - secp256k1 curve
- **RSA Keys** (`KeyPair.generate_rsa()`) - 2048/3072/4096 bit keys
- **EC Keys** (`KeyPair.generate_ec()`) - secp256k1, secp256r1 (P-256) curves

Example with different key types:

```python
from didcomm.crypto import EthKeyPair, KeyPair
from cryptography.hazmat.primitives.asymmetric import ec
from services.protocols import TrustPingHandler

# Ethereum keys
eth_key = EthKeyPair()
handler1 = TrustPingHandler(eth_key, f"did:ethr:{eth_key.address}")

# RSA keys
rsa_key = KeyPair.generate_rsa(key_size=2048)
handler2 = TrustPingHandler(rsa_key, "did:key:rsa:example")

# EC keys
ec_key = KeyPair.generate_ec(curve=ec.SECP256K1())
handler3 = TrustPingHandler(ec_key, "did:key:ec:example")
```

## Testing

All protocol handlers have comprehensive test coverage. Tests are located in `tests/test_protocols/`:

- `test_trust_ping.py` - Tests for Trust Ping protocol
- `test_connection.py` - Tests for Connection protocol

Run tests:
```bash
# Run all protocol tests
python -m pytest tests/test_protocols/ -v

# Run specific protocol tests
python -m pytest tests/test_protocols/test_connection.py -v
```

## Adding New Protocols

To add support for a new Aries protocol:

1. **Create Protocol Handler:** Create a new file in `services/protocols/` (e.g., `my_protocol.py`)

2. **Inherit from ProtocolHandler:**
```python
from services.protocols.base import ProtocolHandler

class MyProtocolHandler(ProtocolHandler):
    protocol_name = "my-protocol"
    supported_versions = ["1.0"]
    
    MSG_TYPE_FOO = "https://didcomm.org/my-protocol/1.0/foo"
    
    async def handle_message(self, message, sender_public_key=None, sender_key_type=None):
        # Implement message handling
        pass
```

3. **Add Schemas:** Add Pydantic schemas to `schemas.py`:
```python
class MyProtocolMessageBody(BaseModel):
    field1: str
    field2: Optional[int] = None

class MyProtocolMessage(BaseModel):
    id: str
    type: str = "https://didcomm.org/my-protocol/1.0/foo"
    body: MyProtocolMessageBody
    # ... other DIDComm fields
```

4. **Register Protocol:** Add to `__init__.py`:
```python
from services.protocols.my_protocol import MyProtocolHandler

PROTOCOL_HANDLERS = {
    "trust-ping": TrustPingHandler,
    "connections": ConnectionHandler,
    "my-protocol": MyProtocolHandler,  # Add here
}
```

5. **Write Tests:** Create comprehensive tests in `tests/test_protocols/test_my_protocol.py`

6. **Update Documentation:** Add protocol documentation to this README

## References

- [Aries RFCs Repository](https://github.com/hyperledger/aries-rfcs)
- [DIDComm Messaging Specification](https://identity.foundation/didcomm-messaging/spec/)
- [DID Core Specification](https://www.w3.org/TR/did-core/)

