"""
TRON multisig wallet cryptography service
Implements N/M multisignature wallets for TRON network
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigdecode_der, sigencode_der
import base58


class SignatureStatus(Enum):
    """Signature validation status"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


@dataclass
class MultisigConfig:
    """
    Configuration for N/M multisig wallet
    
    Attributes:
        required_signatures: N - minimum number of required signatures
        total_owners: M - total number of wallet owners
        owner_addresses: List of TRON owner addresses (base58 format)
        owner_pubkeys: Optional list of owner public keys (hex strings)
        threshold_weight: Optional weight threshold for weighted multisig
        owner_weights: Optional weights for each owner
    """
    required_signatures: int  # N
    total_owners: int  # M
    owner_addresses: List[str]
    owner_pubkeys: Optional[List[str]] = None
    threshold_weight: Optional[int] = None
    owner_weights: Optional[List[int]] = None
    
    def __post_init__(self):
        """Validate configuration"""
        if self.required_signatures < 1:
            raise ValueError("Required signatures (N) must be at least 1")
        
        if self.total_owners < self.required_signatures:
            raise ValueError(
                f"Total owners (M={self.total_owners}) must be >= "
                f"required signatures (N={self.required_signatures})"
            )
        
        if len(self.owner_addresses) != self.total_owners:
            raise ValueError(
                f"Number of addresses ({len(self.owner_addresses)}) "
                f"must equal total owners (M={self.total_owners})"
            )
        
        # Check for duplicate addresses
        if len(set(self.owner_addresses)) != len(self.owner_addresses):
            raise ValueError("Owner addresses must be unique")
        
        # Validate TRON addresses
        for addr in self.owner_addresses:
            if not self._is_valid_tron_address(addr):
                raise ValueError(f"Invalid TRON address: {addr}")
        
        # Validate weighted multisig if configured
        if self.threshold_weight is not None or self.owner_weights is not None:
            if self.threshold_weight is None or self.owner_weights is None:
                raise ValueError("Both threshold_weight and owner_weights must be set for weighted multisig")
            
            if len(self.owner_weights) != self.total_owners:
                raise ValueError("Number of weights must equal total owners")
            
            if self.threshold_weight < 1:
                raise ValueError("Threshold weight must be at least 1")
            
            total_weight = sum(self.owner_weights)
            if self.threshold_weight > total_weight:
                raise ValueError(f"Threshold weight ({self.threshold_weight}) cannot exceed total weight ({total_weight})")
    
    @staticmethod
    def _is_valid_tron_address(address: str) -> bool:
        """Validate TRON address format"""
        try:
            if not address.startswith('T'):
                return False
            if len(address) != 34:
                return False
            # Try to decode base58
            base58.b58decode_check(address)
            return True
        except Exception:
            return False


@dataclass
class MultisigAddress:
    """
    TRON multisig address with metadata
    
    Attributes:
        address: TRON multisig account address (base58)
        hex_address: Hex representation of address
        config: Multisig configuration used
        account_id: TRON account ID (if created on-chain)
        permission_id: Permission ID for multisig (default is 2 for Active permission)
        metadata: Additional data
    """
    address: str
    hex_address: str
    config: MultisigConfig
    account_id: Optional[int] = None
    permission_id: int = 2  # Active permission
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SignatureData:
    """
    Signature data for TRON multisig transaction
    
    Attributes:
        signer_address: TRON address of signer
        signature: Signature bytes (hex string)
        signature_index: Index of signer in multisig config
        public_key: Public key of signer (hex string)
        status: Validation status
        weight: Weight of this signature (for weighted multisig)
        metadata: Additional signature metadata
    """
    signer_address: str
    signature: str
    signature_index: int
    public_key: Optional[str] = None
    status: SignatureStatus = SignatureStatus.PENDING
    weight: int = 1
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MultisigTransaction:
    """
    TRON multisig transaction with signatures
    
    Attributes:
        raw_data: Raw transaction data (hex string)
        raw_data_hex: Transaction raw_data_hex from TRON API
        tx_id: Transaction ID (hash)
        config: Multisig configuration
        signatures: List of signatures
        ref_block_bytes: Reference block bytes
        ref_block_hash: Reference block hash
        expiration: Transaction expiration timestamp
        contract_type: Type of TRON contract (TransferContract, etc.)
        contract_data: Contract-specific data
        metadata: Additional transaction metadata
    """
    raw_data: str
    tx_id: str
    config: MultisigConfig
    signatures: List[SignatureData] = field(default_factory=list)
    raw_data_hex: Optional[str] = None
    ref_block_bytes: Optional[str] = None
    ref_block_hash: Optional[str] = None
    expiration: Optional[int] = None
    contract_type: Optional[str] = None
    contract_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def signatures_count(self) -> int:
        """Get count of valid signatures"""
        return sum(1 for sig in self.signatures if sig.status == SignatureStatus.VALID)
    
    @property
    def total_weight(self) -> int:
        """Get total weight of valid signatures"""
        return sum(sig.weight for sig in self.signatures if sig.status == SignatureStatus.VALID)
    
    @property
    def is_ready_to_broadcast(self) -> bool:
        """Check if transaction has enough signatures to broadcast"""
        if self.config.threshold_weight is not None:
            # Weighted multisig
            return self.total_weight >= self.config.threshold_weight
        else:
            # Standard multisig
            return self.signatures_count >= self.config.required_signatures


class TronMultisig:
    """
    TRON multisig wallet cryptography implementation
    
    Supports both standard N/M multisig and weighted multisig
    """
    
    # TRON address prefix
    TRON_ADDRESS_PREFIX = 0x41
    
    def __init__(self):
        """Initialize TRON multisig handler"""
        pass
    
    @staticmethod
    def address_from_pubkey(pubkey_hex: str) -> str:
        """
        Convert public key to TRON address
        
        Args:
            pubkey_hex: Public key hex string (65 bytes uncompressed)
            
        Returns:
            TRON address in base58 format
        """
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        
        # Remove 0x04 prefix if present (uncompressed key)
        if pubkey_bytes[0] == 0x04:
            pubkey_bytes = pubkey_bytes[1:]
        
        # Keccak256 hash
        keccak = hashlib.sha3_256(pubkey_bytes).digest()
        
        # Take last 20 bytes and add TRON prefix
        address_bytes = bytes([TronMultisig.TRON_ADDRESS_PREFIX]) + keccak[-20:]
        
        # Base58check encoding
        return base58.b58encode_check(address_bytes).decode('utf-8')
    
    @staticmethod
    def address_to_hex(address: str) -> str:
        """
        Convert TRON base58 address to hex
        
        Args:
            address: TRON address in base58 format
            
        Returns:
            Hex address (42 chars with 0x prefix)
        """
        decoded = base58.b58decode_check(address)
        return '0x' + decoded.hex()
    
    @staticmethod
    def hex_to_address(hex_address: str) -> str:
        """
        Convert hex address to TRON base58 address
        
        Args:
            hex_address: Hex address (with or without 0x prefix)
            
        Returns:
            TRON address in base58 format
        """
        if hex_address.startswith('0x'):
            hex_address = hex_address[2:]
        
        address_bytes = bytes.fromhex(hex_address)
        return base58.b58encode_check(address_bytes).decode('utf-8')
    
    def generate_multisig_address(
        self,
        owner_addresses: List[str],
        required_signatures: int,
        salt: Optional[str] = None
    ) -> MultisigAddress:
        """
        Generate deterministic multisig address from owner addresses
        
        This creates a unique TRON address based on the multisig configuration.
        In production, this would be an on-chain account with configured permissions.
        
        Args:
            owner_addresses: List of owner TRON addresses (sorted)
            required_signatures: N - minimum required signatures
            salt: Optional salt for address generation
            
        Returns:
            MultisigAddress with generated address
        """
        # Sort addresses for deterministic generation
        sorted_owners = sorted(owner_addresses)
        
        # Create data for hashing
        data = ''.join(sorted_owners) + str(required_signatures)
        if salt:
            data += salt
        
        # Hash to create deterministic seed
        hash_result = hashlib.sha3_256(data.encode('utf-8')).digest()
        
        # Use hash as "public key" to generate address
        # Take first 64 bytes (32 bytes repeated) to simulate uncompressed pubkey
        pseudo_pubkey = hash_result + hash_result[:32]
        
        # Generate TRON address from pseudo pubkey
        address_hash = hashlib.sha3_256(pseudo_pubkey).digest()
        address_bytes = bytes([self.TRON_ADDRESS_PREFIX]) + address_hash[-20:]
        multisig_address = base58.b58encode_check(address_bytes).decode('utf-8')
        hex_address = self.address_to_hex(multisig_address)
        
        # Create config
        config = MultisigConfig(
            required_signatures=required_signatures,
            total_owners=len(owner_addresses),
            owner_addresses=owner_addresses,
            owner_pubkeys=None,
            threshold_weight=None,
            owner_weights=None
        )
        
        return MultisigAddress(
            address=multisig_address,
            hex_address=hex_address,
            config=config,
            account_id=None,
            permission_id=2,  # Active permission
            metadata={
                'generation_method': 'deterministic',
                'note': 'Demo multisig address. In production, use TRON Account Permission API'
            }
        )
    
    def create_multisig_config(
        self,
        required_signatures: int,
        owner_addresses: List[str],
        owner_pubkeys: Optional[List[str]] = None,
        threshold_weight: Optional[int] = None,
        owner_weights: Optional[List[int]] = None
    ) -> MultisigConfig:
        """
        Create multisig configuration
        
        Args:
            required_signatures: N - minimum required signatures
            owner_addresses: List of TRON owner addresses
            owner_pubkeys: Optional list of public keys
            threshold_weight: Optional weight threshold
            owner_weights: Optional weights for each owner
            
        Returns:
            MultisigConfig
        """
        return MultisigConfig(
            required_signatures=required_signatures,
            total_owners=len(owner_addresses),
            owner_addresses=owner_addresses,
            owner_pubkeys=owner_pubkeys,
            threshold_weight=threshold_weight,
            owner_weights=owner_weights
        )
    
    def prepare_transaction_for_signing(
        self,
        raw_data_hex: str,
        tx_id: str,
        config: MultisigConfig,
        contract_type: Optional[str] = None,
        contract_data: Optional[Dict[str, Any]] = None
    ) -> MultisigTransaction:
        """
        Prepare TRON transaction for multisig signing
        
        Args:
            raw_data_hex: Raw transaction data hex from TRON API
            tx_id: Transaction ID (hash)
            config: Multisig configuration
            contract_type: Type of contract
            contract_data: Contract-specific data
            
        Returns:
            MultisigTransaction ready for signing
        """
        return MultisigTransaction(
            raw_data=raw_data_hex,
            raw_data_hex=raw_data_hex,
            tx_id=tx_id,
            config=config,
            contract_type=contract_type,
            contract_data=contract_data,
            signatures=[]
        )
    
    def sign_transaction(
        self,
        transaction: MultisigTransaction,
        private_key_hex: str,
        signer_address: str
    ) -> MultisigTransaction:
        """
        Sign TRON transaction with owner's private key
        
        Args:
            transaction: Transaction to sign
            private_key_hex: Signer's private key (64 hex chars)
            signer_address: Signer's TRON address
            
        Returns:
            Transaction with added signature
            
        Raises:
            ValueError: If signer is not an owner or already signed
        """
        # Verify signer is an owner
        if signer_address not in transaction.config.owner_addresses:
            raise ValueError(f"Address {signer_address} is not an owner of this multisig wallet")
        
        # Check if already signed
        for sig in transaction.signatures:
            if sig.signer_address == signer_address:
                raise ValueError(f"Address {signer_address} has already signed this transaction")
        
        # Get signer index
        signer_index = transaction.config.owner_addresses.index(signer_address)
        
        # Create signing key
        private_key_bytes = bytes.fromhex(private_key_hex)
        signing_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        
        # Get public key
        verifying_key = signing_key.get_verifying_key()
        public_key_bytes = b'\x04' + verifying_key.to_string()
        public_key_hex = public_key_bytes.hex()
        
        # Sign transaction ID (which is the hash of raw_data)
        tx_id_bytes = bytes.fromhex(transaction.tx_id)
        signature_bytes = signing_key.sign_digest(tx_id_bytes, sigencode=sigencode_der)
        signature_hex = signature_bytes.hex()
        
        # Get weight for this signer
        weight = 1
        if transaction.config.owner_weights:
            weight = transaction.config.owner_weights[signer_index]
        
        # Create signature data
        sig_data = SignatureData(
            signer_address=signer_address,
            signature=signature_hex,
            signature_index=signer_index,
            public_key=public_key_hex,
            status=SignatureStatus.VALID,
            weight=weight
        )
        
        # Add signature to transaction
        transaction.signatures.append(sig_data)
        
        return transaction
    
    def add_external_signature(
        self,
        transaction: MultisigTransaction,
        signature_hex: str,
        signer_address: str,
        public_key_hex: Optional[str] = None
    ) -> MultisigTransaction:
        """
        Add externally created signature (from web wallet like TronLink) to transaction
        
        This method is designed for web wallet integration where private keys are not accessible.
        Web wallets (TronLink, etc.) sign transactions and return the signature, which can be
        added using this method.
        
        Args:
            transaction: Transaction to add signature to
            signature_hex: Signature hex string from web wallet
            signer_address: Signer's TRON address
            public_key_hex: Optional public key hex (for verification)
            
        Returns:
            Transaction with added signature
            
        Raises:
            ValueError: If signer is not an owner or already signed
            
        Example:
            # Frontend (JavaScript with TronLink):
            # const signature = await tronWeb.trx.sign(transaction);
            
            # Backend (Python):
            multisig = TronMultisig()
            transaction = multisig.add_external_signature(
                transaction=tx,
                signature_hex=signature_from_frontend,
                signer_address=user_address,
                public_key_hex=user_pubkey  # Optional
            )
        """
        # Verify signer is an owner
        if signer_address not in transaction.config.owner_addresses:
            raise ValueError(f"Address {signer_address} is not an owner of this multisig wallet")
        
        # Check if already signed
        for sig in transaction.signatures:
            if sig.signer_address == signer_address:
                raise ValueError(f"Address {signer_address} has already signed this transaction")
        
        # Get signer index
        signer_index = transaction.config.owner_addresses.index(signer_address)
        
        # Get weight for this signer
        weight = 1
        if transaction.config.owner_weights:
            weight = transaction.config.owner_weights[signer_index]
        
        # Create signature data
        sig_data = SignatureData(
            signer_address=signer_address,
            signature=signature_hex,
            signature_index=signer_index,
            public_key=public_key_hex,
            status=SignatureStatus.PENDING,  # Will be verified later
            weight=weight
        )
        
        # Verify signature if public key is available
        if public_key_hex:
            try:
                self.verify_signature(transaction, sig_data)
            except Exception as e:
                # If verification fails, still add signature but mark as invalid
                sig_data.status = SignatureStatus.INVALID
                sig_data.metadata = {"verification_error": str(e)}
        
        # Add signature to transaction
        transaction.signatures.append(sig_data)
        
        return transaction
    
    def verify_signature(
        self,
        transaction: MultisigTransaction,
        signature: SignatureData
    ) -> bool:
        """
        Verify a signature on TRON transaction
        
        Args:
            transaction: Transaction that was signed
            signature: Signature to verify
            
        Returns:
            True if signature is valid
        """
        try:
            # Get public key
            if signature.public_key:
                public_key_hex = signature.public_key
            elif transaction.config.owner_pubkeys:
                public_key_hex = transaction.config.owner_pubkeys[signature.signature_index]
            else:
                # Cannot verify without public key
                return False
            
            # Verify address matches public key
            derived_address = self.address_from_pubkey(public_key_hex)
            if derived_address != signature.signer_address:
                return False
            
            # Create verifying key
            public_key_bytes = bytes.fromhex(public_key_hex)
            if public_key_bytes[0] == 0x04:
                public_key_bytes = public_key_bytes[1:]
            
            verifying_key = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)
            
            # Verify signature
            tx_id_bytes = bytes.fromhex(transaction.tx_id)
            signature_bytes = bytes.fromhex(signature.signature)
            
            verifying_key.verify_digest(signature_bytes, tx_id_bytes, sigdecode=sigdecode_der)
            
            # Update status
            signature.status = SignatureStatus.VALID
            return True
            
        except Exception as e:
            signature.status = SignatureStatus.INVALID
            signature.metadata = signature.metadata or {}
            signature.metadata['verification_error'] = str(e)
            return False
    
    def combine_signatures(
        self,
        transaction: MultisigTransaction
    ) -> Dict[str, Any]:
        """
        Combine signatures into final signed transaction for TRON
        
        Args:
            transaction: Transaction with signatures
            
        Returns:
            Dict with signed transaction data ready for broadcast
            
        Raises:
            ValueError: If not enough valid signatures
        """
        # Verify all signatures
        for sig in transaction.signatures:
            if sig.status == SignatureStatus.PENDING:
                self.verify_signature(transaction, sig)
        
        # Check if ready to broadcast
        if not transaction.is_ready_to_broadcast:
            if transaction.config.threshold_weight:
                raise ValueError(
                    f"Not enough signature weight: {transaction.total_weight}/{transaction.config.threshold_weight}"
                )
            else:
                raise ValueError(
                    f"Not enough signatures: {transaction.signatures_count}/{transaction.config.required_signatures}"
                )
        
        # Get valid signatures
        valid_sigs = [sig for sig in transaction.signatures if sig.status == SignatureStatus.VALID]
        
        # Sort signatures by index for consistency
        valid_sigs.sort(key=lambda s: s.signature_index)
        
        # Build TRON transaction format
        signed_transaction = {
            "txID": transaction.tx_id,
            "raw_data_hex": transaction.raw_data_hex,
            "signature": [sig.signature for sig in valid_sigs]
        }
        
        if transaction.contract_data:
            signed_transaction["raw_data"] = transaction.contract_data
        
        return signed_transaction
    
    def get_transaction_weight(
        self,
        transaction: MultisigTransaction
    ) -> Dict[str, Any]:
        """
        Get weight information for transaction
        
        Args:
            transaction: Transaction to analyze
            
        Returns:
            Dict with weight information
        """
        valid_sigs = [sig for sig in transaction.signatures if sig.status == SignatureStatus.VALID]
        
        result = {
            "signatures_count": len(valid_sigs),
            "required_signatures": transaction.config.required_signatures,
            "is_ready": transaction.is_ready_to_broadcast
        }
        
        if transaction.config.threshold_weight:
            result["total_weight"] = transaction.total_weight
            result["threshold_weight"] = transaction.config.threshold_weight
            result["signer_weights"] = {
                sig.signer_address: sig.weight 
                for sig in valid_sigs
            }
        
        return result
    
    @staticmethod
    def calculate_tx_id(raw_data_hex: str) -> str:
        """
        Calculate transaction ID from raw data
        
        Args:
            raw_data_hex: Raw transaction data hex
            
        Returns:
            Transaction ID (SHA256 hash)
        """
        raw_data_bytes = bytes.fromhex(raw_data_hex)
        tx_id = hashlib.sha256(raw_data_bytes).digest()
        return tx_id.hex()

