"""
Cron tasks functions
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import db
from db.models import EscrowModel, EscrowTxnModel
from services.tron.escrow import EscrowService, EscrowError
from services.tron.api_client import TronAPIClient
from services.tron.multisig import TronMultisig, MultisigConfig
from services.tron.utils import private_key_from_mnemonic
from services.arbiter.service import ArbiterService
from services.wallet import WalletService
from settings import Settings

logger = logging.getLogger(__name__)




async def process_escrow_batch(
    session: AsyncSession,
    page: int,
    page_size: int = 10
) -> List[EscrowModel]:
    """
    Получить батч escrow записей с SELECT FOR UPDATE SKIP LOCKED
    
    Args:
        session: Database session
        page: Номер страницы (начиная с 0)
        page_size: Размер страницы
        
    Returns:
        Список заблокированных EscrowModel записей
    """
    # SELECT FOR UPDATE SKIP LOCKED - пропускает заблокированные записи
    stmt = (
        select(EscrowModel)
        .where(
            EscrowModel.status == 'pending'  # Фильтр по статусу
        )
        .order_by(EscrowModel.id)  # Важно: сортировка для стабильной пагинации
        .offset(page * page_size)
        .limit(page_size)
        .with_for_update(skip_locked=True)  # SELECT FOR UPDATE SKIP LOCKED
    )
    
    result = await session.execute(stmt)
    escrows = result.scalars().all()
    
    return list(escrows)


async def _get_or_create_escrow_txn(
    session: AsyncSession,
    escrow_id: int
) -> EscrowTxnModel:
    """
    Получить или создать запись EscrowTxnModel для эскроу
    
    Args:
        session: Database session
        escrow_id: ID эскроу
        
    Returns:
        EscrowTxnModel запись
    """
    stmt = select(EscrowTxnModel).where(EscrowTxnModel.escrow_id == escrow_id)
    result = await session.execute(stmt)
    escrow_txn = result.scalar_one_or_none()
    
    if not escrow_txn:
        escrow_txn = EscrowTxnModel(
            escrow_id=escrow_id,
            type='event',
            comment='',
            txn=None
        )
        session.add(escrow_txn)
        await session.flush()
    
    return escrow_txn


async def _update_escrow_txn(
    session: AsyncSession,
    escrow_txn: EscrowTxnModel,
    txn_type: str,
    comment: str,
    txn_data: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    is_duplicate: bool = False
) -> None:
    """
    Обновить запись EscrowTxnModel
    
    Args:
        session: Database session
        escrow_txn: EscrowTxnModel запись
        txn_type: Тип ('event' или 'txn')
        comment: Комментарий
        txn_data: Данные транзакции (опционально)
        error_code: Код ошибки (опционально)
        error_message: Сообщение об ошибке (опционально)
        is_duplicate: Если True, увеличивает counter на 1 (для дублей событий)
    """
    escrow_txn.type = txn_type
    escrow_txn.comment = comment
    
    # Если это дубль события, увеличиваем счетчик
    if is_duplicate:
        escrow_txn.counter = (escrow_txn.counter or 1) + 1
    
    # Формируем данные для JSONB
    txn_json = {}
    if txn_data:
        txn_json.update(txn_data)
    if error_code:
        txn_json['error_code'] = error_code
    if error_message:
        txn_json['error_message'] = error_message
    
    escrow_txn.txn = txn_json if txn_json else None
    await session.flush()


def _is_same_error(
    escrow_txn: EscrowTxnModel,
    error_code: Optional[str],
    error_message: Optional[str]
) -> bool:
    """
    Проверить, является ли ошибка повторением последней
    
    Args:
        escrow_txn: EscrowTxnModel запись
        error_code: Код ошибки
        error_message: Сообщение об ошибке
        
    Returns:
        True если ошибка повторяется
    """
    if not escrow_txn.txn:
        return False
    
    last_error_code = escrow_txn.txn.get('error_code')
    last_error_message = escrow_txn.txn.get('error_message')
    
    return (
        error_code and error_code == last_error_code and
        error_message and error_message == last_error_message
    )


async def _get_arbiter_private_key(
    session: AsyncSession,
    secret: str
) -> Optional[str]:
    """
    Получить приватный ключ арбитра из активного кошелька арбитра
    
    Args:
        session: Database session
        secret: Секретный ключ для расшифровки мнемоники
        
    Returns:
        Приватный ключ в hex формате или None если арбитр не настроен
    """
    try:
        # Получаем активный кошелек арбитра
        arbiter_wallet = await ArbiterService.get_active_arbiter_wallet(session)
        
        if not arbiter_wallet:
            logger.warning("Active arbiter wallet not found")
            return None
        
        if not arbiter_wallet.encrypted_mnemonic:
            logger.warning(f"Arbiter wallet {arbiter_wallet.id} has no encrypted mnemonic")
            return None
        
        # Расшифровываем мнемоническую фразу
        mnemonic = WalletService.decrypt_mnemonic(
            arbiter_wallet.encrypted_mnemonic,
            secret
        )
        
        # Получаем приватный ключ из мнемоники
        return private_key_from_mnemonic(mnemonic)
        
    except Exception as e:
        logger.error(f"Error getting arbiter private key: {str(e)}", exc_info=True)
        return None


async def _get_escrow_private_key(
    escrow: EscrowModel,
    secret: str
) -> Optional[str]:
    """
    Получить приватный ключ escrow из encrypted_mnemonic
    
    Args:
        escrow: EscrowModel запись
        secret: Секретный ключ для расшифровки мнемоники
        
    Returns:
        Приватный ключ в hex формате или None если мнемоника не настроена
    """
    try:
        if not escrow.encrypted_mnemonic:
            logger.warning(f"Escrow {escrow.id} has no encrypted mnemonic")
            return None
        
        # Расшифровываем мнемоническую фразу
        mnemonic = WalletService.decrypt_mnemonic(
            escrow.encrypted_mnemonic,
            secret
        )
        
        # Получаем приватный ключ из мнемоники
        return private_key_from_mnemonic(mnemonic)
        
    except Exception as e:
        logger.error(f"Error getting escrow private key: {str(e)}", exc_info=True)
        return None


async def _transfer_trx_to_escrow(
    session: AsyncSession,
    escrow: EscrowModel,
    arbiter_address: str,
    arbiter_private_key: str,
    amount: float,
    network: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Перевести TRX на адрес эскроу
    
    Args:
        session: Database session
        escrow: EscrowModel запись
        arbiter_address: Адрес арбитра (откуда переводим)
        arbiter_private_key: Приватный ключ арбитра
        amount: Сумма в TRX
        network: Сеть TRON
        api_key: API ключ TronGrid (опционально)
        
    Returns:
        Dict с результатом операции
    """
    try:
        async with TronAPIClient(network=network, api_key=api_key) as api_client:
            # Создаем транзакцию
            unsigned_tx = await api_client.create_transaction(
                from_address=arbiter_address,
                to_address=escrow.escrow_address,
                amount_trx=amount
            )
            
            if "txID" not in unsigned_tx:
                error_msg = unsigned_tx.get('Error', unsigned_tx.get('message', 'Unknown error'))
                raise Exception(f"Failed to create transaction: {error_msg}")
            
            tx_id = unsigned_tx["txID"]
            raw_data_hex = unsigned_tx["raw_data_hex"]
            
            # Подготавливаем транзакцию для подписи
            multisig = TronMultisig()
            config = MultisigConfig(
                required_signatures=1,
                total_owners=1,
                owner_addresses=[arbiter_address]
            )
            
            transaction = multisig.prepare_transaction_for_signing(
                raw_data_hex=raw_data_hex,
                tx_id=tx_id,
                config=config,
                contract_type="TransferContract"
            )
            
            # Сохраняем contract_data для broadcast
            transaction.contract_data = unsigned_tx.get("raw_data", {})
            
            # Подписываем транзакцию
            transaction = multisig.sign_transaction(
                transaction=transaction,
                private_key_hex=arbiter_private_key,
                signer_address=arbiter_address
            )
            
            # Объединяем подписи
            signed_tx = multisig.combine_signatures(transaction)
            
            # Добавляем visible если нужно
            if "visible" not in signed_tx and "visible" in unsigned_tx:
                signed_tx["visible"] = unsigned_tx["visible"]
            
            # Отправляем транзакцию
            broadcast_result = await api_client.broadcast_transaction(signed_tx)
            
            if broadcast_result.get("result"):
                return {
                    "success": True,
                    "tx_id": tx_id,
                    "amount": amount
                }
            else:
                error_msg = broadcast_result.get('Error', broadcast_result.get('message', 'Unknown error'))
                raise Exception(f"Broadcast failed: {error_msg}")
                
    except Exception as e:
        logger.error(f"Error transferring TRX to escrow {escrow.id}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def _update_escrow_permissions(
    session: AsyncSession,
    escrow: EscrowModel,
    escrow_address: str,
    escrow_private_key: str,
    network: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Обновить permissions эскроу (установить multisig 2/3)
    
    Args:
        session: Database session
        escrow: EscrowModel запись
        escrow_address: Адрес escrow
        escrow_private_key: Приватный ключ escrow
        network: Сеть TRON
        api_key: API ключ TronGrid (опционально)
        
    Returns:
        Dict с результатом операции
    """
    try:
        participant1 = escrow.participant1_address
        participant2 = escrow.participant2_address
        arbiter = escrow.arbiter_address
        
        if not arbiter:
            raise Exception("Arbiter address not set in escrow")
        
        async with TronAPIClient(network=network, api_key=api_key) as api_client:
            # Получаем текущий owner permission (обязательно для обновления)
            account_info = await api_client.get_account(escrow_address)
            
            if not account_info:
                raise Exception(f"Account {escrow_address} not found")
            
            owner_permission = account_info.get("owner_permission")
            if not owner_permission:
                # Если нет owner permission, создаем его с escrow адресом
                owner_permission = {
                    "permission_name": "owner",
                    "threshold": 1,
                    "keys": [{"address": escrow_address, "weight": 1}]
                }
            
            # Формируем permission_data
            # owner: все 3 участника с threshold=2
            # actives: все 3 участника с threshold=2
            permission_data = {
                "owner": {
                    "type": 0,
                    "permission_name": "owner",
                    "threshold": 2,
                    "keys": [
                        {"address": participant1, "weight": 1},
                        {"address": participant2, "weight": 1},
                        {"address": arbiter, "weight": 1}
                    ]
                },
                "actives": [{
                    "type": 2,
                    "permission_name": "multisig_2_of_3",
                    "threshold": 2,
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": [
                        {"address": participant1, "weight": 1},
                        {"address": participant2, "weight": 1},
                        {"address": arbiter, "weight": 1}
                    ]
                }]
            }
            
            # Проверка безопасности: сумма весов >= threshold
            total_weight_owner = sum(key["weight"] for key in permission_data["owner"]["keys"])
            threshold_owner = permission_data["owner"]["threshold"]
            if total_weight_owner < threshold_owner:
                raise Exception(
                    f"Owner permission: сумма весов ({total_weight_owner}) < threshold ({threshold_owner})"
                )
            
            total_weight_active = sum(key["weight"] for key in permission_data["actives"][0]["keys"])
            threshold_active = permission_data["actives"][0]["threshold"]
            if total_weight_active < threshold_active:
                raise Exception(
                    f"Active permission: сумма весов ({total_weight_active}) < threshold ({threshold_active})"
                )
            
            # Создаем транзакцию обновления permissions
            update_tx = await api_client.update_account_permission(
                owner_address=escrow_address,
                permission_data=permission_data
            )
            
            if "txID" not in update_tx:
                error_msg = update_tx.get('Error', update_tx.get('message', 'Unknown error'))
                raise Exception(f"Failed to create update permission transaction: {error_msg}")
            
            tx_id = update_tx["txID"]
            raw_data_hex = update_tx["raw_data_hex"]
            
            # Подготавливаем транзакцию для подписи
            # Для первой установки permissions используем ключ escrow
            multisig = TronMultisig()
            config = MultisigConfig(
                required_signatures=1,
                total_owners=1,
                owner_addresses=[escrow_address]
            )
            
            transaction = multisig.prepare_transaction_for_signing(
                raw_data_hex=raw_data_hex,
                tx_id=tx_id,
                config=config,
                contract_type="AccountPermissionUpdateContract"
            )
            
            # Сохраняем contract_data для broadcast
            transaction.contract_data = update_tx.get("raw_data", {})
            
            # Подписываем транзакцию ключом escrow
            transaction = multisig.sign_transaction(
                transaction=transaction,
                private_key_hex=escrow_private_key,
                signer_address=escrow_address
            )
            
            # Объединяем подписи
            signed_tx = multisig.combine_signatures(transaction)
            
            # Добавляем visible если нужно
            if "visible" not in signed_tx and "visible" in update_tx:
                signed_tx["visible"] = update_tx["visible"]
            
            # Отправляем транзакцию
            broadcast_result = await api_client.broadcast_transaction(signed_tx)
            
            if broadcast_result.get("result"):
                return {
                    "success": True,
                    "tx_id": tx_id
                }
            else:
                error_msg = broadcast_result.get('Error', broadcast_result.get('message', 'Unknown error'))
                raise Exception(f"Broadcast failed: {error_msg}")
                
    except Exception as e:
        logger.error(f"Error updating escrow permissions {escrow.id}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


async def process_escrow(escrow: EscrowModel, session: AsyncSession) -> None:
    """
    Обработать одну escrow запись
    
    Args:
        escrow: EscrowModel запись
        session: Database session
    """
    try:
        logger.info(
            f"Processing escrow ID: {escrow.id}, "
            f"status: {escrow.status}, "
            f"blockchain: {escrow.blockchain}, "
            f"network: {escrow.network}, "
            f"address: {escrow.escrow_address}"
        )
        
        # Получаем настройки
        settings = Settings()
        min_balance = settings.tron.escrow_min_trx_balance
        api_key = settings.tron.api_key
        network = escrow.network
        secret = settings.secret.get_secret_value()
        
        # Получаем или создаем запись EscrowTxnModel
        escrow_txn = await _get_or_create_escrow_txn(session, escrow.id)
        
        # Сначала проверяем, установлены ли permissions
        # Если они уже установлены, то escrow инициализирован и не нужно ничего делать
        async with TronAPIClient(network=network, api_key=api_key) as api_client:
            account_info = await api_client.get_account(escrow.escrow_address)
            
            # Если аккаунт не найден (ещё не активирован в сети) — считаем как нет permissions, идём к пополнению TRX
            if not account_info:
                logger.info(f"Escrow {escrow.id}: account {escrow.escrow_address} not found (not activated), will top up TRX")
                active_permissions = []
            else:
                active_permissions = account_info.get("active_permission", [])
            
            # Проверяем, установлены ли permissions
            has_multisig = False
            
            for perm in active_permissions:
                threshold = perm.get("threshold", 1)
                keys = perm.get("keys", [])
                # Проверяем, есть ли multisig 2/3
                if threshold == 2 and len(keys) == 3:
                    # Проверяем, что все 3 участника присутствуют
                    addresses = {key.get("address") for key in keys}
                    if (
                        escrow.participant1_address in addresses and
                        escrow.participant2_address in addresses and
                        (escrow.arbiter_address in addresses or escrow.escrow_address in addresses)
                    ):
                        has_multisig = True
                        break
            
            # Если permissions уже установлены, обновляем статус и выходим
            if has_multisig:
                logger.info(f"Escrow {escrow.id}: Permissions already set, updating status to active")
                escrow.status = 'active'
                await session.flush()
                await _update_escrow_txn(
                    session, escrow_txn, 'event',
                    "Escrow already initialized: permissions set, status updated to active",
                    txn_data={"type": "already_initialized", "status": "active"}
                )
                return
        
        # Permissions не установлены - проверяем баланс и инициализируем
        async with TronAPIClient(network=network, api_key=api_key) as api_client:
            balance = await api_client.get_balance(escrow.escrow_address)
            logger.info(f"Escrow {escrow.id} balance: {balance:.6f} TRX (min required: {min_balance:.6f} TRX)")
        
        # Если баланс меньше минимума - переводим TRX
        if balance < min_balance:
            amount_needed = min_balance - balance
            logger.info(f"Escrow {escrow.id} needs {amount_needed:.6f} TRX")
            
            # Получаем приватный ключ арбитра
            arbiter_private_key = await _get_arbiter_private_key(session, secret)
            if not arbiter_private_key:
                error_msg = "Active arbiter wallet not found or mnemonic not configured"
                logger.error(f"Escrow {escrow.id}: {error_msg}")
                
                # Проверяем, повторяется ли ошибка
                is_duplicate = _is_same_error(escrow_txn, "ARBITER_MNEMONIC_NOT_CONFIGURED", error_msg)
                await _update_escrow_txn(
                    session, escrow_txn, 'event',
                    f"Error: {error_msg}",
                    error_code="ARBITER_MNEMONIC_NOT_CONFIGURED",
                    error_message=error_msg,
                    is_duplicate=is_duplicate
                )
                return
            
            # Получаем адрес арбитра
            arbiter_address = escrow.arbiter_address
            if not arbiter_address:
                error_msg = "Arbiter address not set in escrow"
                logger.error(f"Escrow {escrow.id}: {error_msg}")
                is_duplicate = _is_same_error(escrow_txn, "ARBITER_ADDRESS_NOT_SET", error_msg)
                await _update_escrow_txn(
                    session, escrow_txn, 'event',
                    f"Error: {error_msg}",
                    error_code="ARBITER_ADDRESS_NOT_SET",
                    error_message=error_msg,
                    is_duplicate=is_duplicate
                )
                return
            
            # Переводим TRX
            transfer_result = await _transfer_trx_to_escrow(
                session, escrow, arbiter_address, arbiter_private_key,
                amount_needed, network, api_key
            )
            
            if transfer_result.get("success"):
                tx_id = transfer_result.get("tx_id")
                logger.info(f"Escrow {escrow.id}: TRX transfer successful, tx_id: {tx_id}")
                await _update_escrow_txn(
                    session, escrow_txn, 'txn',
                    f"TRX transfer: {amount_needed:.6f} TRX to {escrow.escrow_address}",
                    txn_data={"tx_id": tx_id, "amount": amount_needed, "type": "trx_transfer"}
                )
            else:
                error = transfer_result.get("error", "Unknown error")
                logger.error(f"Escrow {escrow.id}: TRX transfer failed: {error}")
                
                # Проверяем, повторяется ли ошибка
                is_duplicate = _is_same_error(escrow_txn, "TRX_TRANSFER_FAILED", error)
                await _update_escrow_txn(
                    session, escrow_txn, 'event',
                    f"Error: TRX transfer failed - {error}",
                    error_code="TRX_TRANSFER_FAILED",
                    error_message=error,
                    is_duplicate=is_duplicate
                )
            return
        
        # Баланс достаточен - обновляем permissions
        # (проверка permissions уже была выполнена выше, поэтому здесь просто обновляем)
        if not has_multisig:
                # Permissions не установлены - обновляем
            logger.info(f"Escrow {escrow.id}: Updating permissions to multisig 2/3")
            
            # Получаем приватный ключ escrow
            escrow_private_key = await _get_escrow_private_key(escrow, secret)
            if not escrow_private_key:
                error_msg = "Escrow encrypted mnemonic not found or not configured"
                logger.error(f"Escrow {escrow.id}: {error_msg}")
                is_duplicate = _is_same_error(escrow_txn, "ESCROW_MNEMONIC_NOT_CONFIGURED", error_msg)
                await _update_escrow_txn(
                    session, escrow_txn, 'event',
                    f"Error: {error_msg}",
                    error_code="ESCROW_MNEMONIC_NOT_CONFIGURED",
                    error_message=error_msg,
                    is_duplicate=is_duplicate
                )
                return
            
            # Обновляем permissions
            update_result = await _update_escrow_permissions(
                session, escrow, escrow.escrow_address, escrow_private_key,
                network, api_key
            )
            
            if update_result.get("success"):
                tx_id = update_result.get("tx_id")
                logger.info(f"Escrow {escrow.id}: Permissions updated successfully, tx_id: {tx_id}")
                await _update_escrow_txn(
                    session, escrow_txn, 'txn',
                    f"Permissions updated: multisig 2/3",
                    txn_data={"tx_id": tx_id, "type": "permission_update"}
                )
                
                # Permissions успешно обновлены - обновляем статус на active
                logger.info(f"Escrow {escrow.id}: Permissions updated, updating status to active")
                escrow.status = 'active'
                await session.flush()
                
                await _update_escrow_txn(
                    session, escrow_txn, 'event',
                    "Escrow initialized: permissions set, status updated to active",
                    txn_data={"type": "initialization_complete", "status": "active"}
                )
            else:
                error = update_result.get("error", "Unknown error")
                logger.error(f"Escrow {escrow.id}: Permission update failed: {error}")
                
                # Проверяем, повторяется ли ошибка
                is_duplicate = _is_same_error(escrow_txn, "PERMISSION_UPDATE_FAILED", error)
                await _update_escrow_txn(
                    session, escrow_txn, 'event',
                    f"Error: Permission update failed - {error}",
                    error_code="PERMISSION_UPDATE_FAILED",
                    error_message=error,
                    is_duplicate=is_duplicate
                )
        
    except Exception as e:
        logger.error(f"Error processing escrow {escrow.id}: {str(e)}", exc_info=True)
        
        # Записываем ошибку в EscrowTxnModel
        try:
            escrow_txn = await _get_or_create_escrow_txn(session, escrow.id)
            error_msg = str(e)
            
            # Проверяем, повторяется ли ошибка
            is_duplicate = _is_same_error(escrow_txn, "PROCESSING_ERROR", error_msg)
            await _update_escrow_txn(
                session, escrow_txn, 'event',
                f"Error: {error_msg}",
                error_code="PROCESSING_ERROR",
                error_message=error_msg,
                is_duplicate=is_duplicate
            )
        except Exception as txn_error:
            logger.error(f"Error updating EscrowTxnModel for escrow {escrow.id}: {str(txn_error)}")
        
        # Не прерываем обработку других эскроу
        raise


async def cron_task():
    """
    Функция, которая выполняется периодически (каждые 5 секунд)
    
    Обрабатывает escrow записи с использованием SELECT FOR UPDATE SKIP LOCKED
    для безопасной параллельной обработки несколькими воркерами.
    
    Блокировки освобождаются после каждого батча (commit), чтобы быстрее
    освобождать записи для других воркеров.
    """
    # Получаем сессию БД динамически
    if db.SessionLocal is None:
        logger.error("Database not initialized. Skipping cron task.")
        return
    
    async with db.SessionLocal() as session:
        try:
            page = 0
            page_size = 10  # Размер батча
            total_processed = 0
            
            while True:
                # Получаем батч записей с блокировкой
                escrows = await process_escrow_batch(session, page, page_size)
                
                if not escrows:
                    # Больше нет записей для обработки
                    break
                
                # Обрабатываем каждую запись
                for escrow in escrows:
                    try:
                        await process_escrow(escrow, session)
                        total_processed += 1
                    except Exception as e:
                        logger.error(f"Failed to process escrow {escrow.id}: {str(e)}")
                        # Продолжаем обработку следующих записей
                        continue
                
                # Коммитим изменения после обработки батча
                # Блокировки освобождаются здесь - записи становятся доступными для других воркеров
                await session.commit()
                
                # Если получили меньше записей, чем page_size, значит это последняя страница
                if len(escrows) < page_size:
                    break
                
                page += 1
                
                # Ограничение: обрабатываем максимум N страниц за один запуск
                # чтобы не блокировать другие задачи
                if page >= 100:  # Максимум 1000 записей за запуск (100 * 10)
                    break
            
            if total_processed > 0:
                logger.info(f"Processed {total_processed} escrow records")
                
        except Exception as e:
            logger.error(f"Error in cron_task: {str(e)}")
            await session.rollback()  # Блокировки освобождаются здесь при ошибке
            raise

