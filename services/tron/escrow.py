"""
TRON Escrow Service for managing multisig escrow operations
Implements 2/3 multisig with 2 participants and 1 arbiter
"""
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import JSONB

from db.models import EscrowModel
from services.tron.api_client import TronAPIClient
from services.tron.multisig import TronMultisig, MultisigConfig


class EscrowError(Exception):
    """Base exception for escrow operations"""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


class EscrowService:
    """
    Service for managing TRON escrow operations with 2/3 multisig
    
    Features:
    - 2 participants + 1 arbiter (2/3 multisig)
    - escrow_address = arbiter address (initially)
    - Auto-detection of arbiter from blockchain permissions
    - Support for TRX and TRC20 payments
    """
    
    # Error codes
    ESCROW_NOT_FOUND = "ESCROW_NOT_FOUND"
    PERMISSIONS_MISMATCH = "PERMISSIONS_MISMATCH"
    ESCROW_NOT_ACTIVATED = "ESCROW_NOT_ACTIVATED"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    INVALID_TOKEN_CONTRACT = "INVALID_TOKEN_CONTRACT"
    INVALID_THRESHOLD = "INVALID_THRESHOLD"
    
    def __init__(self, session: AsyncSession, owner_did: str, api_key: Optional[str] = None):
        """
        Initialize EscrowService
        
        Args:
            session: SQLAlchemy async session
            owner_did: DID пользователя, которому принадлежит escrow
            api_key: Optional TronGrid API key (will be used for all network calls)
        """
        self.session = session
        self.owner_did = owner_did
        self.api_key = api_key
        self.multisig = TronMultisig()
    
    def _get_api_client(self, network: str) -> TronAPIClient:
        """
        Create API client for specific network
        
        Args:
            network: Network name (mainnet, shasta, nile)
            
        Returns:
            TronAPIClient instance for the network
        """
        return TronAPIClient(network=network, api_key=self.api_key)
    
    async def initialize_escrow(
        self,
        participant1: str,
        participant2: str,
        arbiter: str,
        blockchain: str = "tron",
        network: str = "mainnet"
    ) -> EscrowModel:
        """
        Initialize escrow - create new or verify existing
        
        Args:
            participant1: First participant address
            participant2: Second participant address
            arbiter: Arbiter address
            blockchain: Blockchain name (default: "tron")
            network: Network name (default: "mainnet")
            
        Returns:
            EscrowModel instance
            
        Raises:
            EscrowError: If validation fails
        """
        # Check for existing escrow (order of participants doesn't matter)
        existing_escrow = await self._check_existing_escrow(
            participant1, participant2, blockchain, network
        )
        
        if existing_escrow:
            # Verify and update from blockchain
            await self._verify_and_update_escrow(
                existing_escrow, participant1, participant2, arbiter
            )
            return existing_escrow
        else:
            # Create new escrow
            return await self._create_new_escrow(
                participant1, participant2, arbiter, blockchain, network
            )
    
    async def _check_existing_escrow(
        self,
        participant1: str,
        participant2: str,
        blockchain: str,
        network: str,
        wait_if_pending: bool = True,
        timeout_seconds: int = 30
    ) -> Optional[EscrowModel]:
        """
        Find existing escrow by participants (order doesn't matter)
        
        Args:
            participant1: First participant address
            participant2: Second participant address
            blockchain: Blockchain name
            network: Network name
            wait_if_pending: If True, wait for pending escrow to complete
            timeout_seconds: Maximum seconds to wait for pending escrow
            
        Returns:
            EscrowModel if found, None otherwise
            
        Note:
            - Escrow with status 'inactive' are excluded from search
            - If escrow is 'pending' and timeout expires, it's marked as 'inactive' and None is returned
        """
        import asyncio
        from datetime import datetime, timedelta
        
        # Find by participants in any order
        # Exclude inactive escrow (they are considered non-existent)
        stmt = select(EscrowModel).where(
            and_(
                EscrowModel.blockchain == blockchain,
                EscrowModel.network == network,
                EscrowModel.status != 'inactive',  # Exclude inactive escrow
                or_(
                    # participant1, participant2 in that order
                    and_(
                        EscrowModel.participant1_address == participant1,
                        EscrowModel.participant2_address == participant2
                    ),
                    # participant2, participant1 in reverse order
                    and_(
                        EscrowModel.participant1_address == participant2,
                        EscrowModel.participant2_address == participant1
                    )
                )
            )
        )
        
        result = await self.session.execute(stmt)
        escrow = result.scalar_one_or_none()
        
        if not escrow:
            return None
        
        # If escrow is pending and wait is requested
        if escrow.status == 'pending' and wait_if_pending:
            start_time = datetime.utcnow()
            max_wait = timedelta(seconds=timeout_seconds)
            
            while escrow.status == 'pending':
                elapsed = datetime.utcnow() - start_time
                
                if elapsed > max_wait:
                    # Timeout - mark as inactive and return None
                    escrow.status = 'inactive'
                    await self.session.flush()
                    return None
                
                # Wait a bit before checking again
                await asyncio.sleep(2)
                
                # Refresh escrow from database
                await self.session.refresh(escrow)
        
        return escrow
    
    async def _verify_and_update_escrow(
        self,
        escrow: EscrowModel,
        participant1: str,
        participant2: str,
        arbiter: str
    ) -> None:
        """
        Verify escrow permissions in blockchain and update if needed
        
        Args:
            escrow: Existing escrow model
            participant1: First participant address
            participant2: Second participant address
            arbiter: Expected arbiter address
            
        Raises:
            EscrowError: If participants don't match blockchain permissions
        """
        try:
            # Create API client for the escrow's network
            async with self._get_api_client(escrow.network) as api_client:
                # Get account info from blockchain
                account_info = await api_client.get_account(escrow.escrow_address)
                
                if not account_info:
                    raise EscrowError(
                        self.ESCROW_NOT_ACTIVATED,
                        f"Escrow account {escrow.escrow_address} not activated in blockchain",
                        {"escrow_address": escrow.escrow_address}
                    )
                
                # Check for active permissions
                if "active_permission" not in account_info:
                    # No multisig permissions set yet - this is OK for new escrow
                    return
                
                active_permissions = account_info["active_permission"]
                
                # Find last multisig permission (threshold = 2)
                # Take the last one as it represents the most recent permission update
                multisig_perm = None
                for perm in active_permissions:
                    if perm.get("threshold") == 2:
                        multisig_perm = perm
                        # Don't break - continue to get the last one
                
                if not multisig_perm:
                    # No 2/3 multisig found - might not be set up yet
                    return
                
                # Extract addresses from keys
                keys = multisig_perm.get("keys", [])
                addresses_in_blockchain = {key.get("address") for key in keys}
                
                # Check if both participants are present
                if participant1 not in addresses_in_blockchain:
                    raise EscrowError(
                        self.PERMISSIONS_MISMATCH,
                        f"Participant {participant1} not found in blockchain permissions",
                        {
                            "missing_participant": participant1,
                            "blockchain_addresses": list(addresses_in_blockchain)
                        }
                    )
                
                if participant2 not in addresses_in_blockchain:
                    raise EscrowError(
                        self.PERMISSIONS_MISMATCH,
                        f"Participant {participant2} not found in blockchain permissions",
                        {
                            "missing_participant": participant2,
                            "blockchain_addresses": list(addresses_in_blockchain)
                        }
                    )
                
                # Find arbiter (3rd address that is not a participant)
                detected_arbiter = None
                for addr in addresses_in_blockchain:
                    if addr != participant1 and addr != participant2:
                        detected_arbiter = addr
                        break
                
                # Update arbiter if detected and different from current
                if detected_arbiter and detected_arbiter != escrow.arbiter_address:
                    escrow.arbiter_address = detected_arbiter
                    
                    # Update address_roles
                    address_roles = escrow.address_roles.copy() if isinstance(escrow.address_roles, dict) else {}
                    address_roles[detected_arbiter] = "arbiter"
                    escrow.address_roles = address_roles
                    
                    # Update multisig_config
                    config_dict = escrow.multisig_config.copy() if isinstance(escrow.multisig_config, dict) else {}
                    config_dict["owner_addresses"] = [participant1, participant2, detected_arbiter]
                    escrow.multisig_config = config_dict
                    
                    await self.session.flush()
                
                # Update status to active if permissions are confirmed and status is not already active
                if escrow.status != 'active' and multisig_perm:
                    escrow.status = 'active'
                    await self.session.flush()
        
        except EscrowError:
            raise
        except Exception as e:
            raise EscrowError(
                "BLOCKCHAIN_ERROR",
                f"Failed to verify blockchain permissions: {str(e)}",
                {"error": str(e)}
            )
    
    async def _create_new_escrow(
        self,
        participant1: str,
        participant2: str,
        arbiter: str,
        blockchain: str,
        network: str
    ) -> EscrowModel:
        """
        Create new escrow record
        
        Args:
            participant1: First participant address
            participant2: Second participant address
            arbiter: Arbiter address
            blockchain: Blockchain name
            network: Network name
            
        Returns:
            Created EscrowModel
        """
        # Create multisig config (2/3)
        config = self.multisig.create_multisig_config(
            required_signatures=2,
            owner_addresses=[participant1, participant2, arbiter]
        )
        
        # Create address roles mapping
        address_roles = {
            participant1: "participant",
            participant2: "participant",
            arbiter: "arbiter"
        }
        
        # Create escrow model
        # escrow_address = arbiter (as per requirements)
        escrow = EscrowModel(
            blockchain=blockchain,
            network=network,
            escrow_type="multisig",
            escrow_address=arbiter,
            owner_did=self.owner_did,
            participant1_address=participant1,
            participant2_address=participant2,
            multisig_config=config.model_dump(),  # Pydantic model to dict (use model_dump for v2+)
            address_roles=address_roles,
            arbiter_address=arbiter,
            status='pending'  # Initial status
        )
        
        self.session.add(escrow)
        await self.session.flush()
        await self.session.refresh(escrow)
        
        return escrow
    
    async def get_escrow_by_id(self, escrow_id: int) -> EscrowModel:
        """
        Get escrow by ID
        
        Args:
            escrow_id: Escrow ID
            
        Returns:
            EscrowModel
            
        Raises:
            EscrowError: If escrow not found
        """
        stmt = select(EscrowModel).where(EscrowModel.id == escrow_id)
        result = await self.session.execute(stmt)
        escrow = result.scalar_one_or_none()
        
        if not escrow:
            raise EscrowError(
                self.ESCROW_NOT_FOUND,
                f"Escrow with ID {escrow_id} not found",
                {"escrow_id": escrow_id}
            )
        
        return escrow
    
    async def get_escrow_balance(self, escrow_id: int) -> Dict[str, Any]:
        """
        Get escrow balance (TRX and TRC20 tokens)
        
        Args:
            escrow_id: Escrow ID
            
        Returns:
            Dict with balance information
        """
        escrow = await self.get_escrow_by_id(escrow_id)
        
        # Get TRX balance using the escrow's network
        async with self._get_api_client(escrow.network) as api_client:
            trx_balance = await api_client.get_balance(escrow.escrow_address)
        
        return {
            "escrow_id": escrow_id,
            "escrow_address": escrow.escrow_address,
            "trx_balance": trx_balance,
            "blockchain": escrow.blockchain,
            "network": escrow.network
        }
    
    async def create_payment_transaction(
        self,
        escrow_id: int,
        to_address: str,
        amount: float,
        token_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create unsigned payment transaction
        
        Args:
            escrow_id: Escrow ID
            to_address: Recipient address
            amount: Amount to send
            token_contract: TRC20 token contract address (None for TRX)
            
        Returns:
            Dict with unsigned transaction data
            
        Raises:
            EscrowError: If validation fails
        """
        escrow = await self.get_escrow_by_id(escrow_id)
        
        # Get multisig permission ID from blockchain using escrow's network
        async with self._get_api_client(escrow.network) as api_client:
            account_info = await api_client.get_account(escrow.escrow_address)
            
            if not account_info:
                raise EscrowError(
                    self.ESCROW_NOT_ACTIVATED,
                    f"Escrow account {escrow.escrow_address} not activated",
                    {"escrow_address": escrow.escrow_address}
                )
            
            # Find last multisig permission (most recent)
            multisig_permission_id = None
            if "active_permission" in account_info:
                for perm in account_info["active_permission"]:
                    if perm.get("threshold") == 2:
                        multisig_permission_id = perm.get("id")
                        # Don't break - continue to get the last one
            
            if token_contract:
                # TRC20 transaction
                unsigned_tx = await self._create_trc20_transaction(
                    escrow.escrow_address,
                    to_address,
                    amount,
                    token_contract,
                    multisig_permission_id,
                    escrow.network
                )
            else:
                # TRX transaction
                unsigned_tx = await self._create_trx_transaction(
                    escrow.escrow_address,
                    to_address,
                    amount,
                    multisig_permission_id,
                    escrow.network
                )
        
        # Prepare for multisig signing
        config = MultisigConfig(**escrow.multisig_config)
        
        transaction = self.multisig.prepare_transaction_for_signing(
            raw_data_hex=unsigned_tx["raw_data_hex"],
            tx_id=unsigned_tx["txID"],
            config=config,
            contract_type="TransferContract" if not token_contract else "TriggerSmartContract"
        )
        
        # Add contract data for broadcast
        transaction.contract_data = unsigned_tx.get("raw_data", {})
        
        return {
            "escrow_id": escrow_id,
            "transaction": transaction,
            "unsigned_tx": unsigned_tx,
            "required_signatures": config.required_signatures,
            "participants": [
                addr for addr, role in escrow.address_roles.items()
                if role == "participant"
            ],
            "arbiter": escrow.arbiter_address
        }
    
    async def _create_trx_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        permission_id: Optional[int],
        network: str
    ) -> Dict[str, Any]:
        """
        Create TRX transaction
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount in TRX
            permission_id: Permission ID for multisig
            network: Network name
            
        Returns:
            Unsigned transaction
        """
        async with self._get_api_client(network) as api_client:
            # Check balance
            balance = await api_client.get_balance(from_address)
            if balance < amount:
                raise EscrowError(
                    self.INSUFFICIENT_BALANCE,
                    f"Insufficient TRX balance: {balance} < {amount}",
                    {"balance": balance, "required": amount}
                )
            
            # Create transaction
            unsigned_tx = await api_client.create_transaction(
                from_address=from_address,
                to_address=to_address,
                amount_trx=amount,
                permission_id=permission_id
            )
            
            if "txID" not in unsigned_tx:
                raise EscrowError(
                    "TRANSACTION_CREATION_FAILED",
                    f"Failed to create transaction: {unsigned_tx}",
                    {"response": unsigned_tx}
                )
            
            return unsigned_tx
    
    async def _create_trc20_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        token_contract: str,
        permission_id: Optional[int],
        network: str
    ) -> Dict[str, Any]:
        """
        Create TRC20 transaction
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount in tokens
            token_contract: TRC20 contract address
            permission_id: Permission ID for multisig
            network: Network name
            
        Returns:
            Unsigned transaction
        """
        # Validate token contract address
        if not token_contract.startswith('T') or len(token_contract) != 34:
            raise EscrowError(
                self.INVALID_TOKEN_CONTRACT,
                f"Invalid TRC20 contract address: {token_contract}",
                {"token_contract": token_contract}
            )
        
        async with self._get_api_client(network) as api_client:
            # Create TRC20 transfer transaction
            response = await api_client.trigger_smart_contract(
                owner_address=from_address,
                contract_address=token_contract,
                function_selector="transfer(address,uint256)",
                parameter=f"{to_address},{int(amount * 1e6)}",  # Assuming 6 decimals
                permission_id=permission_id
            )
            # TRON API returns { "result": {...}, "transaction": {...} }; we need the transaction object
            unsigned_tx = response.get("transaction") if isinstance(response.get("transaction"), dict) else response
            if not unsigned_tx or "txID" not in unsigned_tx:
                raise EscrowError(
                    "TRANSACTION_CREATION_FAILED",
                    f"Failed to create TRC20 transaction: {response}",
                    {"response": response}
                )
            return unsigned_tx
    
    async def update_arbiter(
        self,
        escrow_id: int,
        new_arbiter: str
    ) -> EscrowModel:
        """
        Update arbiter address (only if permissions allow)
        
        Args:
            escrow_id: Escrow ID
            new_arbiter: New arbiter address
            
        Returns:
            Updated EscrowModel
        """
        escrow = await self.get_escrow_by_id(escrow_id)
        
        # Update arbiter
        escrow.arbiter_address = new_arbiter
        
        # Update address_roles
        address_roles = escrow.address_roles.copy()
        
        # Remove old arbiter
        old_arbiter = None
        for addr, role in list(address_roles.items()):
            if role == "arbiter":
                old_arbiter = addr
                del address_roles[addr]
                break
        
        # Add new arbiter
        address_roles[new_arbiter] = "arbiter"
        escrow.address_roles = address_roles
        
        # Update multisig_config
        config_dict = escrow.multisig_config.copy()
        owner_addresses = config_dict.get("owner_addresses", [])
        
        # Replace old arbiter with new
        if old_arbiter in owner_addresses:
            owner_addresses = [
                new_arbiter if addr == old_arbiter else addr
                for addr in owner_addresses
            ]
        else:
            # Add new arbiter if not replacing
            owner_addresses.append(new_arbiter)
        
        config_dict["owner_addresses"] = owner_addresses
        escrow.multisig_config = config_dict
        
        await self.session.flush()
        await self.session.refresh(escrow)
        
        return escrow
    
    async def update_escrow_status(
        self,
        escrow_id: int,
        status: str,
        tx_id: Optional[str] = None
    ) -> EscrowModel:
        """
        Update escrow status
        
        Args:
            escrow_id: Escrow ID
            status: New status (pending, active, inactive)
            tx_id: Optional transaction ID that changed the status
            
        Returns:
            Updated EscrowModel
        """
        escrow = await self.get_escrow_by_id(escrow_id)
        escrow.status = status
        
        # Optionally store tx_id in metadata (could add status_history JSONB field later)
        # For now, just update the status
        
        await self.session.flush()
        await self.session.refresh(escrow)
        
        return escrow

