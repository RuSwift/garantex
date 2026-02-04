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
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether this key is currently active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<NodeSettings(id={self.id}, key_type={self.key_type}, address={self.ethereum_address})>"


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

