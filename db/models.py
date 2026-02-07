"""
Database models for storing encrypted node settings
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from db import Base


class NodeSettings(Base):
    """Model for storing encrypted mnemonic and PEM data"""
    
    __tablename__ = "node_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Encrypted mnemonic phrase (if using mnemonic)
    encrypted_mnemonic = Column(Text, nullable=True, comment="Encrypted mnemonic phrase")
    
    # Encrypted PEM data (if using PEM key)
    encrypted_pem = Column(Text, nullable=True, comment="Encrypted PEM key data")
    
    # Key type: 'mnemonic' or 'pem'
    key_type = Column(String(20), nullable=False, default='mnemonic', comment="Type of key: mnemonic or pem")
    
    # Ethereum address derived from the key
    ethereum_address = Column(String(42), nullable=True, unique=True, index=True, comment="Ethereum address")
    
    # Service endpoint for DIDComm (e.g. https://node.example.com/endpoint)
    service_endpoint = Column(String(255), nullable=True, comment="Service endpoint URL for DIDComm")
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether this key is currently active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<NodeSettings(id={self.id}, key_type={self.key_type}, address={self.ethereum_address})>"


class AdminUser(Base):
    """Model for storing root admin credentials (single admin only)"""
    
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Password authentication (optional)
    username = Column(String(255), nullable=True, unique=True, index=True, comment="Admin username")
    password_hash = Column(Text, nullable=True, comment="Hashed password (bcrypt)")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AdminUser(id={self.id}, username={self.username})>"


class AdminTronAddress(Base):
    """Model for storing whitelisted TRON addresses for admin authentication"""
    
    __tablename__ = "admin_tron_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    tron_address = Column(String(34), unique=True, nullable=False, index=True, comment="Whitelisted TRON address")
    label = Column(String(255), nullable=True, comment="Optional label for this address")
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether this address is active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AdminTronAddress(id={self.id}, address={self.tron_address}, label={self.label})>"


class WalletUser(Base):
    """Model for storing wallet user profiles (non-admin users)"""
    
    __tablename__ = "wallet_users"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(255), unique=True, nullable=False, index=True, comment="Wallet address (TRON: 34 chars, ETH: 42 chars)")
    blockchain = Column(String(20), nullable=False, index=True, comment="Blockchain type: tron, ethereum, bitcoin, etc.")
    nickname = Column(String(100), nullable=False, comment="User display name")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<WalletUser(id={self.id}, wallet={self.wallet_address}, nickname={self.nickname}, blockchain={self.blockchain})>"


class Storage(Base):
    """Model for storing JSON payloads with space-based organization"""
    
    __tablename__ = "storage"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True, comment="Autoincrement primary key")
    
    uuid = Column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid1, nullable=False, comment="UUID v1 identifier")
    
    # Space identifier for organizing data
    space = Column(String(255), nullable=False, index=True, comment="Space identifier for organizing data")
    
    # Schema version
    schema_ver = Column(String(10), nullable=False, default="1", server_default="1", comment="Schema version")
    
    # JSON payload
    payload = Column(JSONB, nullable=False, comment="JSON payload data")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp (UTC)")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="Last update timestamp (UTC)")
    
    # Create GIN index on JSONB payload for efficient JSON queries
    __table_args__ = (
        Index('ix_storage_payload', 'payload', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Storage(id={self.id}, uuid={self.uuid}, space={self.space})>"


class Connection(Base):
    """Model for storing DIDComm connection protocol states"""
    
    __tablename__ = "connections"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True, comment="Autoincrement primary key")
    
    # Connection identifiers
    connection_id = Column(String(255), unique=True, nullable=False, index=True, comment="Unique connection identifier (message ID)")
    my_did = Column(String(255), nullable=False, index=True, comment="Our DID")
    their_did = Column(String(255), nullable=True, index=True, comment="Their DID (null for pending invitations)")
    
    # Connection status: 'pending' or 'established'
    status = Column(String(20), nullable=False, default='pending', index=True, comment="Connection status")
    
    # Connection type: 'invitation', 'request', 'response'
    connection_type = Column(String(20), nullable=False, comment="Type of connection message")
    
    # Label for display
    label = Column(String(255), nullable=True, comment="Human-readable label")
    
    # Additional metadata (invitation_id, invitation_label, request_id, etc.)
    # Note: cannot use 'metadata' as field name - it's reserved by SQLAlchemy
    connection_metadata = Column(JSONB, nullable=True, comment="Additional connection metadata")
    
    # Original message data (stored as JSON)
    message_data = Column(JSONB, nullable=True, comment="Original DIDComm message data")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp (UTC)")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="Last update timestamp (UTC)")
    established_at = Column(DateTime(timezone=True), nullable=True, comment="When connection was established (UTC)")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('ix_connections_my_did_status', 'my_did', 'status'),
        Index('ix_connections_their_did_status', 'their_did', 'status'),
        Index('ix_connections_connection_metadata', 'connection_metadata', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Connection(id={self.id}, connection_id={self.connection_id}, status={self.status}, my_did={self.my_did}, their_did={self.their_did})>"