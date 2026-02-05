"""
Utility functions for routers
"""
from typing import Optional


def extract_protocol_name(message_type: str) -> Optional[str]:
    """
    Extract protocol name from DIDComm message type URI
    
    Example: "https://didcomm.org/trust-ping/1.0/ping" -> "trust-ping"
    
    Args:
        message_type: Full message type URI
        
    Returns:
        Protocol name or None
    """
    try:
        parts = message_type.split('/')
        if len(parts) >= 4:
            return parts[-3]  # protocol name is third from end
    except Exception:
        pass
    return None

