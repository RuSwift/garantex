# Connection Model - Database Storage for DIDComm Connections

## Overview

The `Connection` model stores the state of DIDComm connection protocol (RFC 0160) in the database. This allows persistent storage of connection invitations, requests, and established connections.

## Model Structure

```python
class Connection(Base):
    __tablename__ = "connections"
    
    # Primary key
    id: BigInteger - Autoincrement primary key
    
    # Connection identifiers
    connection_id: String(255) - Unique connection identifier (message ID)
    my_did: String(255) - Our DID
    their_did: String(255) - Their DID (nullable for pending invitations)
    
    # Status and type
    status: String(20) - 'pending' or 'established'
    connection_type: String(20) - 'invitation', 'request', or 'response'
    
    # Display information
    label: String(255) - Human-readable label
    
    # Additional data
    connection_metadata: JSONB - Additional connection metadata
    message_data: JSONB - Original DIDComm message data
    
    # Timestamps
    created_at: DateTime - Creation timestamp (UTC)
    updated_at: DateTime - Last update timestamp (UTC)
    established_at: DateTime - When connection was established (UTC, nullable)
```

## Indexes

The model includes the following indexes for efficient queries:

- `connection_id` - Unique index
- `my_did` - Regular index
- `their_did` - Regular index
- `status` - Regular index
- `(my_did, status)` - Composite index for filtering connections by owner and status
- `(their_did, status)` - Composite index for finding established connections
- `connection_metadata` - GIN index for JSONB queries

**Note:** The field is named `connection_metadata` instead of `metadata` because `metadata` is a reserved attribute in SQLAlchemy's Declarative API.

## Usage in ConnectionHandler

The `ConnectionHandler` class now requires database initialization:

```python
from db import init_db, SessionLocal
from settings import DatabaseSettings
from didcomm.crypto import EthKeyPair
from services.protocols import ConnectionHandler

# Initialize database first
database_settings = DatabaseSettings()
await init_db(database_settings)

# Now you can create ConnectionHandler
my_key = EthKeyPair()
my_did = f"did:ethr:{my_key.address}"

handler = ConnectionHandler(
    my_key,
    my_did,
    service_endpoint="https://example.com/didcomm"
)

# Create invitation (now async)
invitation = await handler.create_invitation(
    label="My Agent",
    recipient_keys=[my_did]
)

# List connections (now async)
connections = await handler.list_connections()
pending = await handler.list_pending_connections()

# Get specific connection (now async)
connection = await handler.get_connection("did:example:other")
```

## Migration

To create the database table, run:

```bash
# This will be done later - model is ready but migration not created yet
# alembic revision --autogenerate -m "Add connections table"
# alembic upgrade head
```

## Database Initialization Check

The `ConnectionHandler.__init__` now checks if `SessionLocal` is initialized and raises a clear error if not:

```python
try:
    handler = ConnectionHandler(my_key, my_did)
except RuntimeError as e:
    print(e)
    # "Database not initialized. Call db.init_db() before creating ConnectionHandler.
    #  SessionLocal must be initialized to store connection data."
```

## Metadata Examples

### Invitation Metadata
```json
{
  "recipient_keys": ["did:example:key1"],
  "service_endpoint": "https://example.com/didcomm",
  "routing_keys": [],
  "image_url": "https://example.com/avatar.png"
}
```

### Request Metadata
```json
{
  "invitation_id": "uuid-of-invitation",
  "invitation_label": "Alice Agent",
  "did_doc": {
    "@context": "https://w3id.org/did/v1",
    "id": "did:example:123",
    ...
  },
  "recipient_keys": ["did:example:key1"]
}
```

### Established Connection Metadata
```json
{
  "invitation_id": "uuid-of-invitation",
  "invitation_label": "Alice Agent",
  "did_doc": {...},
  "request_id": "uuid-of-request",
  "response_did_doc": {...},
  "response_id": "uuid-of-response"
}
```

## Benefits

1. **Persistence** - Connections survive application restarts
2. **Scalability** - Can handle large numbers of connections efficiently
3. **Auditability** - Full history of connection establishment
4. **Searchability** - Efficient queries with proper indexes
5. **Flexibility** - JSONB metadata allows storing arbitrary connection-specific data

## Notes

- All connection operations are now async (using `await`)
- The handler automatically manages database transactions
- Old in-memory `pending_connections` and `established_connections` dicts are replaced with database queries
- Sessions are automatically closed after each operation

