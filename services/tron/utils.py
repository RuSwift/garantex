"""
Utility functions for TRON blockchain operations
"""
from typing import Tuple
from mnemonic import Mnemonic
from tronpy.keys import PrivateKey as TronPrivateKey
from bip32 import BIP32


def address_from_private_key(private_key_hex: str) -> str:
    """
    Calculate TRON address from private key using tronpy
    
    Args:
        private_key_hex: Private key as hex string (64 characters)
        
    Returns:
        TRON address (base58 encoded)
    """
    # Use tronpy's PrivateKey class for proper TRON address generation
    priv_key = TronPrivateKey(bytes.fromhex(private_key_hex))
    return priv_key.public_key.to_base58check_address()


def private_key_from_mnemonic(mnemonic: str, passphrase: str = "", account_index: int = 0) -> str:
    """
    Generate TRON private key from mnemonic phrase using BIP39/BIP44
    
    Args:
        mnemonic: Mnemonic phrase (12-24 words)
        passphrase: Optional passphrase (BIP39 standard)
        account_index: Account index in BIP44 path (default: 0)
        
    Returns:
        Private key as hex string (64 characters)
    """
    # Generate BIP39 seed
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed(mnemonic, passphrase)
    
    # Create BIP32 HD wallet from seed
    bip32_ctx = BIP32.from_seed(seed)
    
    # BIP44 path for TRON: m/44'/195'/0'/0/{account_index}
    # 44' - BIP44 purpose
    # 195' - TRON coin type
    # 0' - account (hardened)
    # 0 - external chain (receive)
    # account_index - address index
    path = f"m/44'/195'/0'/0/{account_index}"
    
    # Derive private key using BIP32
    derived_key = bip32_ctx.get_privkey_from_path(path)
    
    return derived_key.hex()


def keypair_from_mnemonic(mnemonic: str, passphrase: str = "", account_index: int = 0) -> Tuple[str, str]:
    """
    Generate TRON address and private key from mnemonic phrase
    
    Args:
        mnemonic: Mnemonic phrase (12-24 words)
        passphrase: Optional passphrase
        account_index: Account index in BIP44 path (default: 0)
        
    Returns:
        Tuple of (address, private_key_hex)
    """
    private_key = private_key_from_mnemonic(mnemonic, passphrase, account_index)
    address = address_from_private_key(private_key)
    return address, private_key

