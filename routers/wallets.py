"""
Router for Wallet management API
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, status
from dependencies import RequireAdminDepends, DbDepends, SettingsDepends
from sqlalchemy import select
from db.models import Wallet, WalletUser
from typing import Dict, List

logger = logging.getLogger(__name__)
from schemas.wallet import (
    CreateWalletRequest,
    UpdateWalletNameRequest,
    WalletResponse,
    WalletListResponse,
    UpdatePermissionsRequest,
    UpdatePermissionsResponse,
    CreateUsdtTransactionRequest,
    CreateUsdtTransactionResponse,
    BroadcastUsdtTransactionRequest,
    BroadcastUsdtTransactionResponse
)
from schemas.node import ChangeResponse
from services.wallet import WalletService
from services.tron.api_client import TronAPIClient

router = APIRouter(
    prefix="/api/wallets",
    tags=["wallets"]
)


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    request: CreateWalletRequest,
    db: DbDepends,
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Create a new wallet from mnemonic phrase
    
    Args:
        request: Wallet creation request (name, mnemonic)
        db: Database session
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        Created wallet information
    """
    try:
        wallet = await WalletService.create_wallet(
            name=request.name,
            mnemonic=request.mnemonic,
            db=db,
            secret=settings.secret.get_secret_value()
        )
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            account_permissions=wallet.account_permissions,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating wallet: {str(e)}"
        )


@router.get("", response_model=WalletListResponse)
async def list_wallets(
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get list of all wallets
    
    Args:
        db: Database session
        admin: Admin authentication
        
    Returns:
        List of wallets
    """
    try:
        wallets = await WalletService.get_wallets(db)
        
        wallet_responses = [
            WalletResponse(
                id=wallet.id,
                name=wallet.name,
                tron_address=wallet.tron_address,
                ethereum_address=wallet.ethereum_address,
                account_permissions=wallet.account_permissions,
                created_at=wallet.created_at,
                updated_at=wallet.updated_at
            )
            for wallet in wallets
        ]
        
        return WalletListResponse(
            wallets=wallet_responses,
            total=len(wallet_responses)
        )
    except Exception as e:
        import traceback
        error_detail = str(e)
        # Проверяем, не связана ли ошибка с отсутствием таблицы
        if "does not exist" in error_detail.lower() or "relation" in error_detail.lower():
            error_detail = "Таблица wallets не найдена. Выполните миграцию: alembic upgrade head"
        logger.error(f"Error loading wallets: {error_detail}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading wallets: {error_detail}"
        )


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: int,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get wallet by ID
    
    Args:
        wallet_id: Wallet ID
        db: Database session
        admin: Admin authentication
        
    Returns:
        Wallet information
    """
    try:
        wallet = await WalletService.get_wallet(wallet_id, db)
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            account_permissions=wallet.account_permissions,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading wallet: {str(e)}"
        )


@router.put("/{wallet_id}/name", response_model=WalletResponse)
async def update_wallet_name(
    wallet_id: int,
    request: UpdateWalletNameRequest,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Update wallet name
    
    Args:
        wallet_id: Wallet ID
        request: Update request with new name
        db: Database session
        admin: Admin authentication
        
    Returns:
        Updated wallet information
    """
    try:
        wallet = await WalletService.update_wallet_name(
            wallet_id=wallet_id,
            name=request.name,
            db=db
        )
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            account_permissions=wallet.account_permissions,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating wallet: {str(e)}"
        )


@router.delete("/{wallet_id}", response_model=ChangeResponse)
async def delete_wallet(
    wallet_id: int,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Delete wallet
    
    Args:
        wallet_id: Wallet ID
        db: Database session
        admin: Admin authentication
        
    Returns:
        Success status
    """
    try:
        deleted = await WalletService.delete_wallet(wallet_id, db)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return ChangeResponse(
            success=True,
            message="Wallet deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting wallet: {str(e)}"
        )


@router.post("/{wallet_id}/fetch-permissions", response_model=WalletResponse)
async def fetch_wallet_permissions(
    wallet_id: int,
    db: DbDepends,
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Fetch account permissions from TRON blockchain and update wallet
    
    Args:
        wallet_id: Wallet ID
        db: Database session
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        Updated wallet information with account permissions
    """
    try:
        # Get wallet (только с role = null)
        result = await db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .where(Wallet.role.is_(None))
        )
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Fetch account info from TRON blockchain
        network = settings.tron.network
        api_key = settings.tron.api_key
        
        async with TronAPIClient(network=network, api_key=api_key) as api:
            account_info = await api.get_account(wallet.tron_address)
            
            if not account_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Account {wallet.tron_address} not found in TRON blockchain"
                )
            
            # Extract permissions
            permissions_data = {
                "owner": account_info.get("owner_permission"),
                "active": account_info.get("active_permission", []),
                "witness": account_info.get("witness_permission")
            }
            
            # Update wallet with permissions
            wallet.account_permissions = permissions_data
            await db.commit()
            await db.refresh(wallet)
        
        return WalletResponse(
            id=wallet.id,
            name=wallet.name,
            tron_address=wallet.tron_address,
            ethereum_address=wallet.ethereum_address,
            account_permissions=wallet.account_permissions,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error fetching wallet permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching wallet permissions: {str(e)}"
        )


@router.get("/addresses/{address}/username")
async def get_username_by_address(
    address: str,
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get username by wallet address
    
    Args:
        address: Wallet address (TRON or Ethereum)
        db: Database session
        admin: Admin authentication
        
    Returns:
        Username if found, None otherwise
    """
    try:
        result = await db.execute(
            select(WalletUser).where(WalletUser.wallet_address == address)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return {"username": user.nickname, "found": True}
        else:
            return {"username": None, "found": False}
    except Exception as e:
        logger.error(f"Error getting username by address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting username: {str(e)}"
        )


@router.get("/tron-network")
async def get_tron_network(
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Get TRON network configuration
    
    Args:
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        TRON network name
    """
    return {"network": settings.tron.network}


@router.post("/{wallet_id}/update-permissions", response_model=UpdatePermissionsResponse)
async def create_update_permissions_transaction(
    wallet_id: int,
    request: UpdatePermissionsRequest,
    db: DbDepends,
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Create transaction to update wallet permissions
    
    Args:
        wallet_id: Wallet ID
        request: Permission update configuration
        db: Database session
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        Unsigned transaction for signing
    """
    try:
        # Get wallet (только с role = null)
        result = await db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .where(Wallet.role.is_(None))
        )
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Validate threshold and weights
        total_weight = sum(key.weight for key in request.keys)
        if total_weight < request.threshold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Сумма весов ({total_weight}) меньше threshold ({request.threshold}). Это заблокирует кошелек!"
            )
        
        # Get current owner permission (required for update)
        network = settings.tron.network
        api_key = settings.tron.api_key
        
        async with TronAPIClient(network=network, api_key=api_key) as api:
            account_info = await api.get_account(wallet.tron_address)
            
            if not account_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Account {wallet.tron_address} not found in TRON blockchain"
                )
            
            # Get owner permission (required)
            owner_permission = account_info.get("owner_permission")
            if not owner_permission:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Owner permission not found. Cannot update permissions."
                )
            
            # Prepare permission data
            permission_data = {
                "owner": {
                    "type": 0,
                    "permission_name": owner_permission.get("permission_name", "owner"),
                    "threshold": owner_permission.get("threshold", 1),
                    "keys": owner_permission.get("keys", [])
                },
                "actives": [{
                    "type": 2,
                    "permission_name": request.permission_name,
                    "threshold": request.threshold,
                    "operations": request.operations,
                    "keys": [
                        {
                            "address": key.address,
                            "weight": key.weight
                        }
                        for key in request.keys
                    ]
                }]
            }
            
            # Create update transaction
            #permission_data['actives'][0]['operations'] = '7fff1fc0033e0000000000000000000000000000000000000000000000000000'
            update_tx = await api.update_account_permission(
                owner_address=wallet.tron_address,
                permission_data=permission_data
            )
            
            if "txID" not in update_tx:
                error_msg = update_tx.get("Error", "Unknown error")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create update transaction: {error_msg}"
                )
            
            # Extract transaction data (same format as USDT transaction)
            logger.info(f"Update permissions API response keys: {list(update_tx.keys())}")
            
            transaction_data = update_tx
            tx_id = update_tx.get("txID", "")
            raw_data_hex = update_tx.get("raw_data_hex", "")
            
            # Check if transaction is wrapped in "transaction" key
            if "transaction" in update_tx:
                transaction_data = update_tx["transaction"]
                tx_id = transaction_data.get("txID", update_tx.get("txID", ""))
                raw_data_hex = update_tx.get("raw_data_hex", "")
                logger.info(f"Transaction extracted from 'transaction' key. Has raw_data: {'raw_data' in transaction_data}")
            else:
                transaction_data = update_tx
                tx_id = update_tx.get("txID", "")
                raw_data_hex = update_tx.get("raw_data_hex", "")
                logger.info("Transaction at root level")
            
            # Ensure transaction has raw_data for TronLink
            if "raw_data" not in transaction_data:
                logger.error(f"Transaction does not contain raw_data. Keys: {list(transaction_data.keys())}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Transaction from API does not contain raw_data. Check API response format."
                )
            
            if "contract" not in transaction_data["raw_data"]:
                logger.error(f"Transaction raw_data does not contain contract. raw_data keys: {list(transaction_data['raw_data'].keys())}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Transaction raw_data does not contain contract array"
                )
            
            full_transaction = transaction_data
            logger.info(f"Update permissions transaction prepared for signing. txID: {tx_id}, has raw_data.contract: {'contract' in transaction_data['raw_data']}")
            
            return UpdatePermissionsResponse(
                success=True,
                tx_id=tx_id,
                raw_data_hex=raw_data_hex,
                unsigned_transaction=full_transaction,
                message="Транзакция обновления permissions создана. Требуется подпись для отправки."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating update permissions transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating update permissions transaction: {str(e)}"
        )


@router.post("/create-usdt-transaction", response_model=CreateUsdtTransactionResponse)
async def create_usdt_transaction(
    request: CreateUsdtTransactionRequest,
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Create unsigned USDT (TRC-20) transaction for signing
    
    Args:
        request: USDT transaction parameters
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        Unsigned transaction for signing with TronLink
    """
    try:
        network = settings.tron.network
        api_key = settings.tron.api_key
        
        # USDT contract address (mainnet)
        usdt_contract = request.contract_address
        usdt_decimals = 6  # USDT has 6 decimals
        
        # Convert amount to smallest units
        amount_in_smallest_units = int(request.amount * (10 ** usdt_decimals))
        
        logger.info(f"Creating USDT transaction: {request.from_address} -> {request.to_address}, amount: {request.amount} USDT")

        async with TronAPIClient(network=network, api_key=api_key) as api:
            # Check TRX balance before creating transaction
            trx_balance = await api.get_balance(request.from_address)
            logger.info(f"TRX balance: {trx_balance:.6f} TRX")
            
            # TRC-20 transfers require TRX for energy/bandwidth
            # Minimum recommended: 1 TRX (1000000 SUN)
            if trx_balance < 1.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недостаточно TRX на балансе для оплаты комиссии. Текущий баланс: {trx_balance:.6f} TRX. Рекомендуется минимум 1 TRX."
                )
            
            # Check USDT balance
            usdt_balance = await api.get_trc20_balance(request.from_address, usdt_contract, decimals=usdt_decimals)
            logger.info(f"USDT balance: {usdt_balance:.6f} USDT")
            
            if usdt_balance < request.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недостаточно USDT на балансе. Текущий баланс: {usdt_balance:.6f} USDT, требуется: {request.amount:.6f} USDT"
                )
            
            # Create TRC20 transaction
            unsigned_tx = await api.create_trc20_transaction(
                from_address=request.from_address,
                to_address=request.to_address,
                contract_address=usdt_contract,
                amount=amount_in_smallest_units,
                fee_limit=10_000_000  # 10 TRX fee limit
            )
            
            if "txID" not in unsigned_tx and "transaction" not in unsigned_tx:
                error_msg = unsigned_tx.get("Error", "Unknown error")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create USDT transaction: {error_msg}"
                )
            
            # Extract transaction data
            # API /wallet/triggersmartcontract can return in different formats:
            # Format 1: {transaction: {raw_data: {...}, txID: "...", ...}, raw_data_hex: "...", energy_used: ...}
            # Format 2: {raw_data: {...}, txID: "...", raw_data_hex: "...", ...}
            
            # Log API response structure for debugging
            logger.info(f"API response keys: {list(unsigned_tx.keys())}")
            
            # Check if transaction is wrapped in "transaction" key (Format 1)
            if "transaction" in unsigned_tx:
                # Transaction is wrapped: extract it
                transaction_data = unsigned_tx["transaction"]
                tx_id = transaction_data.get("txID", "")
                raw_data_hex = unsigned_tx.get("raw_data_hex", "")
                logger.info(f"Transaction extracted from 'transaction' key. Has raw_data: {'raw_data' in transaction_data}")
            else:
                # Transaction is at root level (Format 2)
                transaction_data = unsigned_tx
                tx_id = unsigned_tx.get("txID", "")
                raw_data_hex = unsigned_tx.get("raw_data_hex", "")
                logger.info("Transaction at root level")
            
            # TronLink expects transaction with raw_data at root level
            # Format: {raw_data: {...}, txID: "...", ...}
            # Ensure transaction has raw_data
            if "raw_data" not in transaction_data:
                logger.error(f"Transaction does not contain raw_data. Keys: {list(transaction_data.keys())}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Transaction from API does not contain raw_data. Check API response format."
                )
            
            # Verify raw_data has contract array
            if "contract" not in transaction_data["raw_data"]:
                logger.error(f"Transaction raw_data does not contain contract. raw_data keys: {list(transaction_data['raw_data'].keys())}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Transaction raw_data does not contain contract array"
                )
            
            # Use transaction_data directly (it has raw_data, txID, etc.)
            full_transaction = transaction_data
            logger.info(f"Transaction prepared for signing. txID: {tx_id}, has raw_data.contract: {'contract' in transaction_data['raw_data']}")
            
            return CreateUsdtTransactionResponse(
                success=True,
                tx_id=tx_id,
                unsigned_transaction=full_transaction,
                raw_data_hex=raw_data_hex,
                message="Транзакция USDT создана. Требуется подпись для отправки."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating USDT transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating USDT transaction: {str(e)}"
        )


@router.post("/broadcast-usdt-transaction", response_model=BroadcastUsdtTransactionResponse)
async def broadcast_usdt_transaction(
    request: BroadcastUsdtTransactionRequest,
    settings: SettingsDepends,
    admin: RequireAdminDepends
):
    """
    Broadcast signed USDT transaction to TRON network
    
    Args:
        request: Signed transaction from TronLink
        settings: Application settings
        admin: Admin authentication
        
    Returns:
        Broadcast result
    """
    try:
        network = settings.tron.network
        api_key = settings.tron.api_key
        
        logger.info("Broadcasting signed USDT transaction")
        
        async with TronAPIClient(network=network, api_key=api_key) as api:
            # Broadcast transaction
            result = await api.broadcast_transaction(request.signed_transaction)
            
            if result.get("result") == True:
                txid = result.get("txid", request.signed_transaction.get("txID", ""))
                logger.info(f"USDT transaction broadcasted successfully: {txid}")
                
                # Wait a bit for transaction to be included in a block
                await asyncio.sleep(3)
                
                # Check transaction status
                try:
                    tx_info = await api.get_transaction_info(txid)
                    if tx_info:
                        receipt = tx_info.get('receipt', {})
                        receipt_result = receipt.get('result', 'UNKNOWN')
                        
                        if receipt_result == 'SUCCESS':
                            logger.info(f"Transaction executed successfully: {txid}")
                            return BroadcastUsdtTransactionResponse(
                                success=True,
                                result=True,
                                txid=txid,
                                message="Транзакция USDT успешно выполнена!"
                            )
                        elif receipt_result == 'FAILED' or receipt_result == 'REVERT':
                            # Transaction was included but reverted
                            error_msg = receipt.get('result_message', 'Transaction reverted')
                            logger.error(f"Transaction reverted: {txid}, reason: {error_msg}")
                            
                            # Try to get more details
                            contract_result = receipt.get('contractResult', [])
                            if contract_result:
                                error_msg = contract_result[0] if isinstance(contract_result, list) else str(contract_result)
                            
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Транзакция откатилась (Transaction Revert). Причина: {error_msg}. Возможные причины: недостаточно TRX для оплаты энергии, недостаточно USDT на балансе, или ошибка в смарт-контракте."
                            )
                        else:
                            # Transaction is pending or unknown status
                            logger.warning(f"Transaction status unknown: {receipt_result}")
                            return BroadcastUsdtTransactionResponse(
                                success=True,
                                result=True,
                                txid=txid,
                                message=f"Транзакция отправлена в блокчейн. Статус: {receipt_result}. Проверьте статус в TronScan через несколько секунд."
                            )
                    else:
                        # Transaction not yet confirmed
                        logger.warning(f"Transaction not yet confirmed: {txid}")
                        return BroadcastUsdtTransactionResponse(
                            success=True,
                            result=True,
                            txid=txid,
                            message="Транзакция отправлена в блокчейн. Ожидается подтверждение. Проверьте статус в TronScan через несколько секунд."
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning(f"Could not check transaction status: {str(e)}")
                    # Still return success if broadcast was successful
                    return BroadcastUsdtTransactionResponse(
                        success=True,
                        result=True,
                        txid=txid,
                        message="Транзакция отправлена в блокчейн. Проверьте статус в TronScan."
                    )
            else:
                error_msg = result.get("message", result.get("Error", "Unknown error"))
                logger.error(f"Failed to broadcast USDT transaction: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ошибка отправки USDT транзакции: {error_msg}"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error broadcasting USDT transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error broadcasting USDT transaction: {str(e)}"
        )

