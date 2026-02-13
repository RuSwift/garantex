"""
Utility functions for working with DIDs and other ledger-related identifiers
"""

def get_user_did(wallet_address: str, blockchain: str) -> str:
    """
    Формирует DID из wallet_address и blockchain
    
    Args:
        wallet_address: Адрес кошелька пользователя
        blockchain: Тип блокчейна (tron, ethereum, bitcoin, etc.)
        
    Returns:
        DID строка в формате did:{method}:{address}
    """
    blockchain_lower = blockchain.lower()
    
    if blockchain_lower in ['tron', 'ethereum', 'bitcoin']:
        # TRON, Ethereum, Bitcoin use secp256k1
        did_method = "ethr" if blockchain_lower == "ethereum" else blockchain_lower
        did = f"did:{did_method}:{wallet_address.lower()}"
    elif blockchain_lower in ['polkadot', 'substrate']:
        # Polkadot uses Ed25519
        did = f"did:polkadot:{wallet_address.lower()}"
    else:
        # Default to secp256k1 for unknown blockchains
        did = f"did:ethr:{wallet_address.lower()}"
    
    return did

