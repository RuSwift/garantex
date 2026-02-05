"""
DIDComm message handling router

This router handles incoming DIDComm messages and routes them
to appropriate protocol handlers.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from dependencies import PrivKeyDepends, SettingsDepends
from didcomm.message import DIDCommMessage, unpack_message
from didcomm.did import create_peer_did_from_keypair
from services.protocols import get_protocol_handler, ProtocolHandler


router = APIRouter(prefix="/api/didcomm", tags=["DIDComm"])


class DIDCommMessageRequest(BaseModel):
    """Request body for incoming DIDComm messages"""
    message: Dict[str, Any] = Field(..., description="Packed DIDComm message")
    sender_public_key: Optional[str] = Field(None, description="Sender's public key (hex)")
    sender_key_type: Optional[str] = Field(None, description="Sender's key type (ETH, RSA, EC)")


class DIDCommMessageResponse(BaseModel):
    """Response for DIDComm message handling"""
    success: bool = Field(..., description="Whether message was handled successfully")
    message: Optional[str] = Field(None, description="Status message")
    response: Optional[Dict[str, Any]] = Field(None, description="Response message if any")


@router.post("/message", response_model=DIDCommMessageResponse)
async def handle_didcomm_message(
    request: DIDCommMessageRequest,
    priv_key: PrivKeyDepends,
    settings: SettingsDepends
):
    """
    Handle incoming DIDComm message
    
    This endpoint receives packed DIDComm messages, unpacks them,
    routes them to the appropriate protocol handler, and returns
    any response message.
    
    Args:
        request: Packed DIDComm message
        priv_key: Node's private key (from dependencies)
        settings: Node settings (from dependencies)
        
    Returns:
        Response indicating success and optional response message
    """
    # Check if node is initialized
    if not settings.is_node_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node not initialized. Please initialize the node first."
        )
    
    if priv_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node key not available"
        )
    
    try:
        # Convert sender public key from hex if provided
        sender_public_key = None
        if request.sender_public_key:
            sender_public_key = bytes.fromhex(request.sender_public_key)
        
        # Unpack the message
        message = unpack_message(
            request.message,
            priv_key,
            sender_public_key=sender_public_key,
            sender_key_type=request.sender_key_type
        )
        
        # Extract protocol name from message type
        protocol_name = extract_protocol_name(message.type)
        if not protocol_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not determine protocol from message type: {message.type}"
            )
        
        # Get protocol handler
        handler_class = get_protocol_handler(protocol_name)
        if not handler_class:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Protocol '{protocol_name}' is not supported"
            )
        
        # Create handler instance with node's key and DID
        did_obj = create_peer_did_from_keypair(priv_key)
        handler: ProtocolHandler = handler_class(priv_key, did_obj.did)
        
        # Handle the message
        response_message = await handler.handle_message(
            message,
            sender_public_key=sender_public_key,
            sender_key_type=request.sender_key_type
        )
        
        # If handler returns a response, pack it
        response_data = None
        if response_message:
            # Get recipient's public key (from original message sender)
            if sender_public_key:
                packed_response = handler.pack_response(
                    response_message,
                    [sender_public_key],
                    encrypt=True
                )
                response_data = packed_response
        
        return DIDCommMessageResponse(
            success=True,
            message=f"Message handled successfully by {protocol_name} protocol",
            response=response_data
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.post("/send-ping")
async def send_trust_ping(
    recipient_did: str,
    response_requested: bool = True,
    comment: Optional[str] = None,
    priv_key: PrivKeyDepends = Depends(),
    settings: SettingsDepends = Depends()
):
    """
    Send a Trust Ping message to another DID
    
    This is a convenience endpoint for testing connectivity
    with other DIDComm agents.
    
    Args:
        recipient_did: DID of the recipient
        response_requested: Whether to request a pong response
        comment: Optional comment to include
        priv_key: Node's private key
        settings: Node settings
        
    Returns:
        Packed Trust Ping message ready to send
    """
    # Check if node is initialized
    if not settings.is_node_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node not initialized"
        )
    
    if priv_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node key not available"
        )
    
    try:
        # Import here to avoid circular imports
        from services.protocols import TrustPingHandler
        
        # Create handler
        did_obj = create_peer_did_from_keypair(priv_key)
        handler = TrustPingHandler(priv_key, did_obj.did)
        
        # Create ping message
        ping_message = handler.create_ping(
            recipient_did=recipient_did,
            response_requested=response_requested,
            comment=comment
        )
        
        # Note: In a real implementation, you'd need the recipient's public key
        # to pack the message. For now, we return the unpacked message.
        # The caller needs to pack it with the recipient's public key.
        
        return {
            "success": True,
            "message": ping_message.to_dict(),
            "note": "This is an unpacked message. You need to pack it with recipient's public key before sending."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating ping message: {str(e)}"
        )


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

