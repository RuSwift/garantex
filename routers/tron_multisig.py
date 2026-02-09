"""
TRON Multisig API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.tron import TronMultisig, MultisigConfig, MultisigTransaction
from services.tron.api_client import TronAPIClient
from services.tron.utils import keypair_from_mnemonic
from dependencies import SettingsDepends
import os

router = APIRouter(prefix="/api/multisig", tags=["tron-multisig"])

# Хранилище транзакций в памяти (для демо)
transactions_storage: Dict[str, MultisigTransaction] = {}

# Session storage (для демо)
demo_config: Optional[MultisigConfig] = None
owner_addresses: Dict[str, str] = {}
owner_keys: Dict[str, str] = {}


# Pydantic models
class GetConfigResponse(BaseModel):
    success: bool
    config: Dict[str, Any]
    message: str


class CheckPermissionsRequest(BaseModel):
    owner_address: str


class CheckPermissionsResponse(BaseModel):
    success: bool
    has_multisig: bool
    permission_id: Optional[int] = None
    permission_name: Optional[str] = None
    threshold: Optional[int] = None
    keys_count: Optional[int] = None
    message: str


class CreateTransactionRequest(BaseModel):
    from_address: str
    to_address: str
    amount_trx: float
    permission_id: int


class CreateTransactionResponse(BaseModel):
    success: bool
    tx_id: str
    raw_data_hex: str
    contract_data: Dict[str, Any]
    unsigned_transaction: Dict[str, Any]  # Full transaction for TronLink
    message: str


class AddSignatureRequest(BaseModel):
    tx_id: str
    signature: str
    signer_address: str


class AddSignatureResponse(BaseModel):
    success: bool
    signatures_count: int
    required_signatures: int
    is_ready: bool
    message: str


class BroadcastTransactionRequest(BaseModel):
    tx_id: str


class BroadcastTransactionResponse(BaseModel):
    success: bool
    result: bool
    txid: str
    message: str


@router.get("/config")
async def get_config():
    """
    Получить конфигурацию мультиподписи из мнемоник
    """
    global demo_config, owner_addresses, owner_keys
    
    try:
        # Получить мнемоники из env
        mnemonic1 = os.getenv("MNEMONIC1")
        mnemonic2 = os.getenv("MNEMONIC2")
        mnemonic3 = os.getenv("MNEMONIC3")
        
        if not all([mnemonic1, mnemonic2, mnemonic3]):
            raise HTTPException(
                status_code=400, 
                detail="Необходимо установить MNEMONIC1, MNEMONIC2, MNEMONIC3 в переменных окружения"
            )
        
        # Generate keypairs
        owner1_address, owner1_key = keypair_from_mnemonic(mnemonic1)
        owner2_address, owner2_key = keypair_from_mnemonic(mnemonic2)
        owner3_address, owner3_key = keypair_from_mnemonic(mnemonic3)
        
        # Store for later use
        owner_addresses = {
            "owner1": owner1_address,
            "owner2": owner2_address,
            "owner3": owner3_address
        }
        owner_keys = {
            "owner1": owner1_key,
            "owner2": owner2_key,
            "owner3": owner3_key
        }
        
        # Create multisig config (2 of 3)
        multisig = TronMultisig()
        demo_config = multisig.create_multisig_config(
            required_signatures=2,
            owner_addresses=[owner1_address, owner2_address, owner3_address]
        )
        
        print(f"✅ Multisig config loaded:")
        print(f"   Owner1: {owner1_address}")
        print(f"   Owner2: {owner2_address}")
        print(f"   Owner3: {owner3_address}")
        print(f"   Required signatures: {demo_config.required_signatures}/{demo_config.total_owners}")
        
        return GetConfigResponse(
            success=True,
            config={
                "required_signatures": demo_config.required_signatures,
                "total_owners": demo_config.total_owners,
                "owner_addresses": demo_config.owner_addresses,
                "owner1_address": owner1_address,
                "owner2_address": owner2_address,
                "owner3_address": owner3_address
            },
            message=f"Конфигурация 2/3 создана. Owner1: {owner1_address[:10]}..."
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-permissions")
async def check_permissions(
    request: CheckPermissionsRequest,
    settings: SettingsDepends
):
    """
    Проверить multisig permissions аккаунта в TRON Mainnet
    """
    try:
        network = settings.tron.network
        api_key = settings.tron.api_key
        print(f"🔍 Checking permissions on TRON {network.upper()} for {request.owner_address}")
        
        async with TronAPIClient(network=network, api_key=api_key) as api:
            account_info = await api.get_account(request.owner_address)
            
            if not account_info or "active_permission" not in account_info:
                print(f"   ⚠ No active permissions found")
                return CheckPermissionsResponse(
                    success=True,
                    has_multisig=False,
                    message="Аккаунт не имеет multisig permissions"
                )
            
            active_permissions = account_info["active_permission"]
            print(f"   Found {len(active_permissions)} active permission(s)")
            
            # Check for multisig permission
            for perm in active_permissions:
                threshold = perm.get("threshold", 1)
                keys = perm.get("keys", [])
                permission_name = perm.get("permission_name", "active")
                permission_id = perm.get("id")
                
                # Это multisig если threshold > 1 или ключей больше 1
                is_multisig = threshold > 1 or len(keys) > 1
                
                print(f"   Permission: {permission_name} (ID: {permission_id})")
                print(f"      Threshold: {threshold}, Keys: {len(keys)}, Multisig: {is_multisig}")
                
                if is_multisig and permission_name == "multisig_2_of_3":
                    print(f"   ✅ Multisig permission found!")
                    return CheckPermissionsResponse(
                        success=True,
                        has_multisig=True,
                        permission_id=permission_id,
                        permission_name=permission_name,
                        threshold=threshold,
                        keys_count=len(keys),
                        message=f"Найден multisig permission в {network.upper()}: {permission_name} (ID: {permission_id})"
                    )
            
            print(f"   ⚠ No multisig_2_of_3 permission found")
            return CheckPermissionsResponse(
                success=True,
                has_multisig=False,
                message="Multisig permission не найден"
            )
    
    except Exception as e:
        import traceback
        print(f"❌ Check permissions error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-transaction")
async def create_transaction(
    request: CreateTransactionRequest,
    settings: SettingsDepends
):
    """
    Создать транзакцию в TRON Mainnet с multisig permission
    """
    try:
        network = settings.tron.network
        api_key = settings.tron.api_key
        print(f"🔨 Creating transaction on TRON {network.upper()}...")
        print(f"   From: {request.from_address}")
        print(f"   To: {request.to_address}")
        print(f"   Amount: {request.amount_trx} TRX")
        print(f"   Permission ID: {request.permission_id}")
        
        async with TronAPIClient(network=network, api_key=api_key) as api:
            unsigned_tx = await api.create_transaction(
                from_address=request.from_address,
                to_address=request.to_address,
                amount_trx=request.amount_trx,
                permission_id=request.permission_id
            )
            
            if "txID" not in unsigned_tx:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка создания транзакции: {unsigned_tx}"
                )
            
            tx_id = unsigned_tx["txID"]
            raw_data_hex = unsigned_tx["raw_data_hex"]
            contract_data = unsigned_tx.get("raw_data", {})
            visible = unsigned_tx.get("visible", True)
            
            print(f"✅ Transaction created on Mainnet: {tx_id}")
            print(f"   Has raw_data: {'raw_data' in unsigned_tx}")
            print(f"   Has raw_data_hex: {'raw_data_hex' in unsigned_tx}")
            print(f"   visible: {visible}")
            
            # Prepare for multisig
            multisig = TronMultisig()
            transaction = multisig.prepare_transaction_for_signing(
                raw_data_hex=raw_data_hex,
                tx_id=tx_id,
                config=demo_config,
                contract_type="TransferContract"
            )
            
            # Add contract_data and visible for broadcast
            transaction.contract_data = contract_data
            
            # Store visible flag in metadata for later use
            if transaction.metadata is None:
                transaction.metadata = {}
            transaction.metadata["visible"] = visible
            
            # Store transaction
            transactions_storage[tx_id] = transaction
            
            return CreateTransactionResponse(
                success=True,
                tx_id=tx_id,
                raw_data_hex=raw_data_hex,
                contract_data=contract_data,
                unsigned_transaction=unsigned_tx,  # Full transaction for TronLink
                message=f"Транзакция создана в Mainnet: {tx_id[:16]}..."
            )
    
    except Exception as e:
        import traceback
        print(f"❌ Create transaction error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-signature")
async def add_signature(request: AddSignatureRequest):
    """
    Добавить подпись от пользователя (через Web Wallet)
    """
    global demo_config, owner_keys, owner_addresses
    
    try:
        print(f"📝 Adding signature from {request.signer_address}")
        
        if request.tx_id not in transactions_storage:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = transactions_storage[request.tx_id]
        multisig = TronMultisig()
        
        print(f"   Current signatures: {transaction.signatures_count}/{transaction.config.required_signatures}")
        print(f"   Signer address: {request.signer_address}")
        print(f"   Expected owners: {transaction.config.owner_addresses}")
        
        # Check if signer is in the owner list
        if request.signer_address not in transaction.config.owner_addresses:
            print(f"   ❌ ERROR: Signer {request.signer_address} is NOT in owner list!")
            print(f"   Expected one of:")
            for i, addr in enumerate(transaction.config.owner_addresses):
                print(f"      Owner{i+1}: {addr}")
            raise HTTPException(
                status_code=400,
                detail=f"Address {request.signer_address} is not an owner. Check TronLink wallet matches MNEMONIC1."
            )
        
        # Verify and clean signature format
        signature_hex = request.signature
        
        # Remove 0x prefix if present
        if signature_hex.startswith('0x') or signature_hex.startswith('0X'):
            signature_hex = signature_hex[2:]
            print(f"   Removed 0x prefix from signature")
        
        print(f"   Signature length: {len(signature_hex)} chars")
        print(f"   Signature (first 64): {signature_hex[:64]}...")
        print(f"   Signature (last 2 chars - recovery): {signature_hex[-2:]}")
        
        # Add user signature (use cleaned signature_hex)
        transaction = multisig.add_external_signature(
            transaction=transaction,
            signature_hex=signature_hex,
            signer_address=request.signer_address,
            public_key_hex=None
        )
        
        print(f"   ✓ User signature added")
        print(f"   Signatures now: {transaction.signatures_count}/{transaction.config.required_signatures}")
        print(f"   Transaction signatures list:")
        for i, sig in enumerate(transaction.signatures):
            print(f"      {i+1}. {sig.signer_address} (status: {sig.status.value})")
        
        # Update storage
        transactions_storage[request.tx_id] = transaction
        
        # Check if we need more signatures
        signatures_needed = transaction.config.required_signatures - transaction.signatures_count
        
        print(f"   Signatures needed: {signatures_needed}")
        
        # Auto-sign with owner2 if needed
        if signatures_needed > 0:
            print(f"   🤖 Auto-signing with owner2...")
            print(f"      Owner2 address: {owner_addresses.get('owner2', 'NOT SET')}")
            print(f"      Owner2 key exists: {bool(owner_keys.get('owner2'))}")
            print(f"      Owner2 key (first 16): {owner_keys.get('owner2', 'NOT SET')[:16]}...")
            
            if not owner_addresses.get("owner2") or not owner_keys.get("owner2"):
                print(f"   ❌ ERROR: Owner2 credentials not set!")
                print(f"      Available keys: {list(owner_keys.keys())}")
                print(f"      Available addresses: {list(owner_addresses.keys())}")
            else:
                try:
                    # Check that owner2 address matches the key
                    from services.tron.utils import address_from_private_key
                    derived_address = address_from_private_key(owner_keys["owner2"])
                    print(f"      Derived address from key: {derived_address}")
                    print(f"      Expected address: {owner_addresses['owner2']}")
                    print(f"      Match: {derived_address == owner_addresses['owner2']}")
                    
                    transaction = multisig.sign_transaction(
                        transaction=transaction,
                        private_key_hex=owner_keys["owner2"],
                        signer_address=owner_addresses["owner2"]
                    )
                    transactions_storage[request.tx_id] = transaction
                    print(f"   ✅ Owner2 signature added!")
                    print(f"      Signatures now: {transaction.signatures_count}/{transaction.config.required_signatures}")
                    
                    # Print all signatures for debug with hex details
                    for i, sig in enumerate(transaction.signatures):
                        print(f"      Signature {i+1}: {sig.signer_address} (status: {sig.status.value})")
                        print(f"         Hex (first 64): {sig.signature[:64]}...")
                        print(f"         Recovery byte: {sig.signature[-2:]}")
                        
                except Exception as e:
                    print(f"   ❌ Auto-sign error: {e}")
                    import traceback
                    traceback.print_exc()
        
        return AddSignatureResponse(
            success=True,
            signatures_count=transaction.signatures_count,
            required_signatures=transaction.config.required_signatures,
            is_ready=transaction.is_ready_to_broadcast,
            message="Подпись добавлена" + (" (автоподпись выполнена)" if transaction.is_ready_to_broadcast else "")
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast")
async def broadcast_transaction(
    request: BroadcastTransactionRequest,
    settings: SettingsDepends
):
    """
    Отправить транзакцию в TRON Mainnet
    """
    try:
        network = settings.tron.network
        api_key = settings.tron.api_key
        
        if request.tx_id not in transactions_storage:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = transactions_storage[request.tx_id]
        
        if not transaction.is_ready_to_broadcast:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно подписей: {transaction.signatures_count}/{transaction.config.required_signatures}"
            )
        
        # Combine signatures
        multisig = TronMultisig()
        signed_tx = multisig.combine_signatures(transaction)
        
        # Add visible flag from metadata (important for TRON API)
        if transaction.metadata and "visible" in transaction.metadata:
            signed_tx["visible"] = transaction.metadata["visible"]
            print(f"   Added visible={signed_tx['visible']} to transaction")
        
        # Log before broadcast
        print(f"📡 Broadcasting transaction to TRON {network.upper()}...")
        print(f"   TX ID: {request.tx_id}")
        print(f"   Signatures: {transaction.signatures_count}/{transaction.config.required_signatures}")
        print(f"   Transaction structure:")
        print(f"      Has txID: {'txID' in signed_tx}")
        print(f"      Has raw_data: {'raw_data' in signed_tx}")
        print(f"      Has raw_data_hex: {'raw_data_hex' in signed_tx}")
        print(f"      Has signature: {'signature' in signed_tx}")
        print(f"      Has visible: {'visible' in signed_tx}")
        print(f"      Signatures count: {len(signed_tx.get('signature', []))}")
        
        # Print each signature with recovery byte
        if 'signature' in signed_tx:
            for i, sig in enumerate(signed_tx['signature']):
                print(f"      Signature {i+1}:")
                print(f"         Hex: {sig[:64]}... (len: {len(sig)})")
                print(f"         Recovery byte (last 2 chars): {sig[-2:]}")
                print(f"         Signer (from transaction): {transaction.signatures[i].signer_address}")
        
        if 'raw_data' in signed_tx:
            print(f"      raw_data keys: {list(signed_tx['raw_data'].keys())}")
            if 'contract' in signed_tx['raw_data']:
                print(f"      contract count: {len(signed_tx['raw_data']['contract'])}")
        else:
            print(f"      ❌ WARNING: raw_data is missing!")
            print(f"      transaction.contract_data: {transaction.contract_data}")
        
        # Broadcast to TRON network
        async with TronAPIClient(network=network, api_key=api_key) as api:
            result = await api.broadcast_transaction(signed_tx)
            
            print(f"   Broadcast result: {result}")
            
            if result.get("result"):
                print(f"✅ Transaction broadcast successful!")
                print(f"   TronScan: https://tronscan.org/#/transaction/{result.get('txid', request.tx_id)}")
                
                return BroadcastTransactionResponse(
                    success=True,
                    result=True,
                    txid=result.get("txid", request.tx_id),
                    message=f"Транзакция отправлена в TRON Mainnet! TX: {result.get('txid', request.tx_id)}"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка broadcast в mainnet: {result}"
                )
    
    except Exception as e:
        import traceback
        print(f"❌ Broadcast error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transaction/{tx_id}")
async def get_transaction_status(tx_id: str):
    """
    Получить статус транзакции
    """
    if tx_id not in transactions_storage:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction = transactions_storage[tx_id]
    
    return {
        "success": True,
        "tx_id": tx_id,
        "signatures_count": transaction.signatures_count,
        "required_signatures": transaction.config.required_signatures,
        "is_ready": transaction.is_ready_to_broadcast,
        "signatures": [
            {
                "signer_address": sig.signer_address,
                "status": sig.status.value
            }
            for sig in transaction.signatures
        ]
    }


@router.get("/reset")
async def reset_data():
    """
    Сбросить данные сессии
    """
    global demo_config, owner_addresses, owner_keys, transactions_storage
    demo_config = None
    owner_addresses = {}
    owner_keys = {}
    transactions_storage = {}
    
    return {
        "success": True,
        "message": "Данные сессии сброшены"
    }
