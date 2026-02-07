"""
TRON Multisig API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.tron import TronMultisig, MultisigConfig, MultisigTransaction
import secrets

router = APIRouter(prefix="/api/multisig", tags=["tron-multisig"])

# Тестовые приватные ключи (НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ!)
# Эти ключи сгенерированы для тестирования и НЕ содержат реальных средств
TEST_KEYS = {
    "owner1": {
        # Пользователь - подписывает через TronLink
        # Мнемоника: pyramid copper syrup license leisure language brick core cream grief glass lazy
        "address": "TBzoUzcPQ2FWsRY4vhNh2nqkrSsYtJkAwY",
        "private_key": None  # Подписывается через TronLink
    },
    "owner2": {
        # Автоматическая подпись 1 (из мнемоники: destroy render width tilt crunch nerve urban adapt capital access romance salon)
        "address": "TL8px7fxRmPuUhA4pe26eFaaP8qfZAsoMe",
        "private_key": "74b1e6cc8ffad5e10e5b7d6ea62ef48dcf4da3f1074b3fb795d9d5b69e63bb14"
    },
    "owner3": {
        # Автоматическая подпись 2 (из мнемоники: diet dose swamp truth taxi useful text run exotic enforce puzzle hard)
        "address": "TJoozVQS3vzaPcfChKk3GGR13pw1aUJdSk",
        "private_key": "86dd65f9df09f0db2c69b89a0a7afc6a6bb96bbb5f0e46e13ee7e8bb2bedc54e"
    }
}

# Хранилище транзакций в памяти (для демо)
transactions_storage: Dict[str, MultisigTransaction] = {}

# Конфигурация мультиподписи (для демо)
demo_config: Optional[MultisigConfig] = None

# Multisig address (для демо)
from services.tron.multisig import MultisigAddress
demo_multisig_address: Optional[MultisigAddress] = None


class AddSignatureRequest(BaseModel):
    tx_id: str
    signature: str
    signer_address: str
    public_key_hex: Optional[str] = None


class CreateTestConfigResponse(BaseModel):
    success: bool
    config: Dict[str, Any]
    message: str


@router.get("/test/config")
async def get_test_config():
    """
    Получить тестовую конфигурацию мультиподписи 2/3 и сгенерировать multisig адрес
    """
    global demo_config, demo_multisig_address
    
    try:
        multisig = TronMultisig()
        
        # Создать конфигурацию 2/3 (нужно 2 подписи из 3)
        owner_addresses = [
            TEST_KEYS["owner1"]["address"],  # Пользователь
            TEST_KEYS["owner2"]["address"],  # Авто-подпись 1
            TEST_KEYS["owner3"]["address"],  # Авто-подпись 2
        ]
        
        print(f"Creating config with addresses: {owner_addresses}")
        
        # Генерировать детерминированный multisig адрес
        demo_multisig_address = multisig.generate_multisig_address(
            owner_addresses=owner_addresses,
            required_signatures=2,
            salt="garantex_demo_v1"
        )
        
        demo_config = demo_multisig_address.config
        
        print(f"Config created successfully: {demo_config.required_signatures}/{demo_config.total_owners}")
        print(f"Multisig address generated: {demo_multisig_address.address}")
        
        return CreateTestConfigResponse(
            success=True,
            config={
                "required_signatures": demo_config.required_signatures,
                "total_owners": demo_config.total_owners,
                "owner_addresses": demo_config.owner_addresses,
                "user_address": TEST_KEYS["owner1"]["address"],
                "multisig_address": demo_multisig_address.address,
                "multisig_hex_address": demo_multisig_address.hex_address
            },
            message=f"Создан multisig кошелек {demo_config.required_signatures}/{demo_config.total_owners}: {demo_multisig_address.address}"
        )
    except ValueError as e:
        print(f"ValueError in config creation: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        print(f"Exception in config creation: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/add-signature")
async def add_signature(request: AddSignatureRequest):
    """
    Добавить подпись от пользователя (через TronLink)
    """
    global demo_config
    
    try:
        multisig = TronMultisig()
        
        # Если транзакции нет в хранилище, создать её автоматически
        if request.tx_id not in transactions_storage:
            if not demo_config:
                raise HTTPException(status_code=400, detail="Config not initialized. Call /test/config first")
            
            print(f"Creating new transaction for tx_id: {request.tx_id}")
            # Создать транзакцию с минимальными данными
            # raw_data_hex будет пустым, так как мы работаем только с подписями
            transaction = multisig.prepare_transaction_for_signing(
                raw_data_hex="",  # Пустой, так как транзакция уже создана в TronWeb
                tx_id=request.tx_id,
                config=demo_config,
                contract_type="TransferContract"
            )
            transactions_storage[request.tx_id] = transaction
        else:
            transaction = transactions_storage[request.tx_id]
        
        # Добавить подпись от пользователя
        print(f"Adding signature from {request.signer_address} for tx {request.tx_id}")
        transaction = multisig.add_external_signature(
            transaction=transaction,
            signature_hex=request.signature,
            signer_address=request.signer_address,
            public_key_hex=request.public_key_hex
        )
        
        # Обновить в хранилище
        transactions_storage[request.tx_id] = transaction
        print(f"Signature added. Current count: {transaction.signatures_count}/{transaction.config.required_signatures}")
        
        # Проверить, нужны ли еще подписи
        signatures_needed = transaction.config.required_signatures - transaction.signatures_count
        
        # Если нужна еще одна подпись, автоматически подписать вторым владельцем
        if signatures_needed > 0 and signatures_needed < transaction.config.required_signatures:
            # Автоматически подписать owner2 (для демо)
            try:
                transaction = multisig.sign_transaction(
                    transaction=transaction,
                    private_key_hex=TEST_KEYS["owner2"]["private_key"],
                    signer_address=TEST_KEYS["owner2"]["address"]
                )
                transactions_storage[request.tx_id] = transaction
            except Exception as e:
                # Если owner2 уже подписал, попробовать owner3
                try:
                    transaction = multisig.sign_transaction(
                        transaction=transaction,
                        private_key_hex=TEST_KEYS["owner3"]["private_key"],
                        signer_address=TEST_KEYS["owner3"]["address"]
                    )
                    transactions_storage[request.tx_id] = transaction
                except:
                    pass  # Уже достаточно подписей
        
        return {
            "success": True,
            "signatures_count": transaction.signatures_count,
            "required_signatures": transaction.config.required_signatures,
            "is_ready": transaction.is_ready_to_broadcast,
            "message": "Подпись добавлена" + (" (автоподпись выполнена)" if transaction.is_ready_to_broadcast else "")
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/prepare-transaction")
async def prepare_test_transaction(raw_data_hex: str, tx_id: str):
    """
    Подготовить транзакцию для подписи (для теста)
    """
    global demo_config
    
    if not demo_config:
        raise HTTPException(status_code=400, detail="Config not initialized. Call /test/config first")
    
    try:
        multisig = TronMultisig()
        
        # Подготовить транзакцию
        transaction = multisig.prepare_transaction_for_signing(
            raw_data_hex=raw_data_hex,
            tx_id=tx_id,
            config=demo_config,
            contract_type="TransferContract"
        )
        
        # Сохранить в хранилище
        transactions_storage[tx_id] = transaction
        
        return {
            "success": True,
            "tx_id": tx_id,
            "message": "Транзакция готова к подписи"
        }
    except Exception as e:
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
        "tx_id": tx_id,
        "signatures_count": transaction.signatures_count,
        "required_signatures": transaction.config.required_signatures,
        "is_ready": transaction.is_ready_to_broadcast,
        "signatures": [
            {
                "signer_address": sig.signer_address,
                "status": sig.status.value,
                "signature_index": sig.signature_index
            }
            for sig in transaction.signatures
        ]
    }


@router.post("/transaction/{tx_id}/finalize")
async def finalize_transaction(tx_id: str):
    """
    Финализировать транзакцию (объединить подписи)
    """
    if tx_id not in transactions_storage:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction = transactions_storage[tx_id]
    
    try:
        multisig = TronMultisig()
        signed_tx = multisig.combine_signatures(transaction)
        
        return {
            "success": True,
            "signed_transaction": signed_tx,
            "message": "Транзакция готова к broadcast"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/reset")
async def reset_test_data():
    """
    Сбросить тестовые данные
    """
    global demo_config, demo_multisig_address, transactions_storage
    demo_config = None
    demo_multisig_address = None
    transactions_storage = {}
    
    return {
        "success": True,
        "message": "Тестовые данные сброшены"
    }
