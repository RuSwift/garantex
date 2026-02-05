"""
Aries protocol handlers for DIDComm messaging

This package provides implementations of Aries RFC protocols
with support for various cryptographic key types (Ethereum, RSA, EC).
"""

from services.protocols.base import ProtocolHandler
from services.protocols.trust_ping import TrustPingHandler
from services.protocols.schemas import (
    TrustPingMessage,
    TrustPingResponse,
    TrustPingBody,
    TrustPingResponseBody,
    BasicMessage,
    BasicMessageBody,
    TimingDecorator
)

__all__ = [
    "ProtocolHandler",
    "TrustPingHandler",
    "TrustPingMessage",
    "TrustPingResponse",
    "TrustPingBody",
    "TrustPingResponseBody",
    "BasicMessage",
    "BasicMessageBody",
    "TimingDecorator",
]


# Protocol registry for automatic routing
PROTOCOL_HANDLERS = {
    "trust-ping": TrustPingHandler,
}


def get_protocol_handler(protocol_name: str):
    """
    Get protocol handler class by protocol name
    
    Args:
        protocol_name: Name of the protocol (e.g., "trust-ping")
        
    Returns:
        Protocol handler class or None if not found
    """
    return PROTOCOL_HANDLERS.get(protocol_name)

