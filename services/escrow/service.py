"""
Escrow Service for managing escrow operations
Supports multiple blockchains and escrow types (multisig, contract)
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from db.models import EscrowModel
from services.tron.multisig import TronMultisig
from services.node import NodeService
from didcomm.crypto import EthCrypto


class EscrowService:
    """
    Service for managing escrow operations
    
    Features:
    - Support for multiple blockchains (tron, eth, etc.)
    - Support for multiple escrow types (multisig, contract)
    - Automatic escrow creation and lookup
    """
    
    def __init__(
        self,
        session: AsyncSession,
        owner_did: str,
        secret: str,
        escrow_type: str = 'multisig',
        blockchain: str = 'tron',
        network: str = "mainnet"
    ):
        """
        Initialize EscrowService
        
        Args:
            session: SQLAlchemy async session
            owner_did: DID пользователя, которому принадлежит escrow
            secret: Secret key for encryption
            escrow_type: Escrow type (multisig | contract)
            blockchain: Blockchain name (tron, eth, etc.)
            network: Network name (mainnet, testnet, etc.) - default: "mainnet"
        """
        if escrow_type not in ["multisig", "contract"]:
            raise ValueError(f"Invalid escrow_type: {escrow_type}. Must be 'multisig' or 'contract'")
        
        self.session = session
        self.blockchain = blockchain
        self.owner_did = owner_did
        self.secret = secret
        self.escrow_type = escrow_type
        self.network = network
        if escrow_type == 'multisig' and blockchain == 'tron':
            self.multisig = TronMultisig()
        else:
            raise RuntimeError('Unexpected behaviour')
    
    async def ensure_exists(
        self,
        arbiter_address: str,
        sender_address: str,
        receiver_address: str
    ) -> EscrowModel:
        """
        Ensure escrow exists - find existing or create new
        
        Args:
            arbiter_address: Arbiter address
            sender_address: Sender/participant 1 address
            receiver_address: Receiver/participant 2 address
            
        Returns:
            EscrowModel instance (existing or newly created)
        """
        # Check for existing escrow by participants (order doesn't matter)
        stmt = select(EscrowModel).where(
            and_(
                EscrowModel.blockchain == self.blockchain,
                EscrowModel.network == self.network,
                EscrowModel.escrow_type == self.escrow_type,
                EscrowModel.owner_did == self.owner_did,
                EscrowModel.status != 'inactive',  # Exclude inactive escrow
                or_(
                    # sender, receiver in that order
                    and_(
                        EscrowModel.participant1_address == sender_address,
                        EscrowModel.participant2_address == receiver_address
                    ),
                    # receiver, sender in reverse order
                    and_(
                        EscrowModel.participant1_address == receiver_address,
                        EscrowModel.participant2_address == sender_address
                    )
                ),
                # Also check arbiter address
                EscrowModel.arbiter_address == arbiter_address
            )
        )
        
        result = await self.session.execute(stmt)
        existing_escrow = result.scalar_one_or_none()
        
        if existing_escrow:
            return existing_escrow
        
        # Create new escrow
        # Map addresses: sender -> participant1, receiver -> participant2
        participant1_address = sender_address
        participant2_address = receiver_address
        
        # Determine escrow_address based on type
        if self.escrow_type == "multisig":
            # For multisig, escrow_address = arbiter_address
            escrow_address = arbiter_address
            
            # Create multisig config (2/3)
            config = self.multisig.create_multisig_config(
                required_signatures=2,
                owner_addresses=[participant1_address, participant2_address, arbiter_address]
            )
            multisig_config = config.model_dump()
        else:
            # For contract type, escrow_address = arbiter_address (can be changed later)
            escrow_address = arbiter_address
            # Minimal config for contract type
            multisig_config = {
                "required_signatures": 2,
                "owner_addresses": [participant1_address, participant2_address, arbiter_address]
            }
        
        # Create address roles mapping
        address_roles = {
            participant1_address: "participant",
            participant2_address: "participant",
            arbiter_address: "arbiter"
        }
        
        # Generate and encrypt mnemonic for escrow wallet management
        mnemonic = EthCrypto.generate_mnemonic(strength=128)  # 12 words
        encrypted_mnemonic = NodeService.encrypt_data(mnemonic, self.secret)
        
        # Create escrow model
        escrow = EscrowModel(
            blockchain=self.blockchain,
            network=self.network,
            escrow_type=self.escrow_type,
            escrow_address=escrow_address,
            owner_did=self.owner_did,
            participant1_address=participant1_address,
            participant2_address=participant2_address,
            multisig_config=multisig_config,
            address_roles=address_roles,
            arbiter_address=arbiter_address,
            encrypted_mnemonic=encrypted_mnemonic,
            status='pending'  # Initial status
        )
        
        self.session.add(escrow)
        await self.session.flush()
        await self.session.refresh(escrow)
        
        return escrow

