import os
import sys
import asyncio
import subprocess
import tempfile

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

from services.tron.utils import address_from_private_key, private_key_from_mnemonic, keypair_from_mnemonic
from services.tron.api_client import TronAPIClient
from services.tron.multisig import TronMultisig, MultisigConfig

mnemonic1 = os.getenv("MNEMONIC1")
mnemonic2 = os.getenv("MNEMONIC2")
mnemonic3 = os.getenv("MNEMONIC3")
mnemonic4 = os.getenv("MNEMONIC4")
mnemonic5 = os.getenv("MNEMONIC5")
mnemonic6 = os.getenv("MNEMONIC6")
mnemonic7 = os.getenv("MNEMONIC7")
mnemonic8 = os.getenv("MNEMONIC8")
mnemonic9 = os.getenv("MNEMONIC9")


async def example_full_multisig_workflow():
    """Example: Complete multisig workflow with mainnet (Account Permission approach)"""
    print("=" * 60)
    print("Полный workflow multisig с mainnet")
    print("(Account Permission - нативная мультиподпись TRON)")
    print("=" * 60)
    
    if not all([mnemonic1, mnemonic2, mnemonic3]):
        print("❌ Ошибка: Необходимо установить MNEMONIC1, MNEMONIC2, MNEMONIC3")
        return
    
    # Generate keypairs from mnemonics
    owner1_address, owner1_key = keypair_from_mnemonic(mnemonic1)
    owner2_address, owner2_key = keypair_from_mnemonic(mnemonic2)
    owner3_address, owner3_key = keypair_from_mnemonic(mnemonic3)
    
    print(f"Owner 1 (main account): {owner1_address}")
    print(f"Owner 2 (co-signer): {owner2_address}")
    print(f"Owner 3 (co-signer): {owner3_address}")
    print()
    print("💡 Multisig будет настроен для Owner 1 аккаунта")
    print("   Все транзакции с него потребуют 2 из 3 подписей")
    print()
    
    async with TronAPIClient(network="mainnet") as api:
        multisig = TronMultisig()
        
        # Create multisig config (2 of 3)
        config = multisig.create_multisig_config(
            required_signatures=2,
            owner_addresses=[owner1_address, owner2_address, owner3_address]
        )
        
        print(f"✓ Конфигурация 2/3 создана")
        print(f"  Владельцы: {config.total_owners}")
        print(f"  Требуется подписей: {config.required_signatures}")
        print()
        
        # Generate multisig address (для идентификации/справки)
        multisig_addr = multisig.generate_multisig_address(
            owner_addresses=[owner1_address, owner2_address, owner3_address],
            required_signatures=2,
            salt="example_demo"
        )
        
        print(f"📋 Multisig ID (для справки): {multisig_addr.address}")
        print()
        
        # ШАГ 0: Обновить Account Permissions
        print("Шаг 0: Обновление Account Permissions")
        print("-" * 40)
        print(f"Проверка текущих permissions для {owner1_address[:10]}...")
        
        # Проверяем текущие permissions
        has_multisig = False
        try:
            current_account = await api.get_account(owner1_address)
            
            if current_account and "active_permission" in current_account:
                current_permissions = current_account["active_permission"]
                
                # Проверяем, является ли это реальным multisig
                # Дефолтный аккаунт имеет: threshold=1, 1 ключ, name="active"
                for perm in current_permissions:
                    threshold = perm.get("threshold", 1)
                    keys = perm.get("keys", [])
                    permission_name = perm.get("permission_name", "active")
                    
                    # Это multisig если:
                    # 1. Threshold > 1 (требуется больше 1 подписи)
                    # 2. Ключей больше 1 (несколько владельцев)
                    # 3. Имя permission изменено (не дефолтное "active")
                    is_custom_multisig = (
                        threshold > 1 or 
                        len(keys) > 1 or 
                        (permission_name != "active" and permission_name != "")
                    )
                    
                    if is_custom_multisig:
                        has_multisig = True
                        
                        print()
                        print("⚠️  Аккаунт УЖЕ имеет multisig permissions!")
                        print(f"  Текущая конфигурация:")
                        print(f"    Permission: {permission_name}")
                        print(f"    Threshold: {threshold}")
                        print(f"    Ключи: {len(keys)}")
                        for key in keys:
                            addr = key.get("address", "")
                            weight = key.get("weight", 0)
                            print(f"      - {addr[:10]}... (вес: {weight})")
                        
                        print()
                        print("  💡 Для изменения permissions потребуется:")
                        print(f"     {threshold} подписей согласно текущим правилам")
                        print()
                        print("  ⏭️  Пропускаем обновление permissions (уже установлены)")
                        print()
                        break
                
                if not has_multisig:
                    print()
                    print("  ✓ Аккаунт имеет дефолтные permissions (не multisig)")
                    print(f"    Текущие: threshold={current_permissions[0].get('threshold', 1)}, ключей={len(current_permissions[0].get('keys', []))}")
                    print("    Можно установить multisig без дополнительных подписей")
                    print()
            else:
                print()
                print("  ✓ Аккаунт не имеет active_permission")
                print("    Можно установить multisig")
                print()
        except Exception as e:
            print(f"  ⚠️  Ошибка проверки аккаунта: {e}")
            print()
        
        # Если нет multisig, создаём транзакцию обновления
        if not has_multisig:
            # Проверить баланс перед обновлением permissions
            balance_trx = await api.get_balance(owner1_address)
            print(f"Баланс аккаунта: {balance_trx:.2f} TRX")
            
            if balance_trx < 100:  # AccountPermissionUpdate может требовать до 100 TRX
                print(f"⚠️  ВНИМАНИЕ: Баланс {balance_trx:.2f} TRX может быть недостаточен")
                print(f"   AccountPermissionUpdate обычно требует ~100 TRX (fee limit)")
                print(f"   Рекомендуется иметь минимум 150 TRX")
                print()
                print(f"❌ Недостаточно средств для обновления permissions")
                print(f"   Пополните аккаунт {owner1_address}")
                print()
                return
            
            print("Создание транзакции обновления permissions...")
            
            # ВАЖНО: При обновлении permissions ВСЕГДА нужно указывать:
            # 1. owner - права владельца аккаунта (обязательно!)
            # 2. actives - права для операций (наш multisig)
            permission_data = {
                "owner": {
                    "type": 0,
                    "permission_name": "owner",
                    "threshold": 1,
                    "keys": [
                        {"address": owner1_address, "weight": 1}
                    ]
                },
                "actives": [{
                    "type": 2,
                    "permission_name": "multisig_2_of_3",
                    "threshold": config.required_signatures,
                    "operations": "7fff1fc0033e0000000000000000000000000000000000000000000000000000",
                    "keys": [
                        {"address": owner1_address, "weight": 1},
                        {"address": owner2_address, "weight": 1},
                        {"address": owner3_address, "weight": 1}
                    ]
                }]
            }
            
            # Проверка безопасности: сумма весов >= threshold
            total_weight = sum(key["weight"] for key in permission_data["actives"][0]["keys"])
            threshold = permission_data["actives"][0]["threshold"]
            
            if total_weight < threshold:
                print(f"❌ ОПАСНО! Сумма весов ({total_weight}) < threshold ({threshold})")
                print("   Аккаунт будет ЗАБЛОКИРОВАН навсегда!")
                return
            
            print(f"  ✓ Проверка безопасности: {total_weight} >= {threshold}")
            print()
        
        try:
            if not has_multisig:
                update_tx = await api.update_account_permission(
                    owner_address=owner1_address,
                    permission_data=permission_data
                )
                
                if "txID" in update_tx:
                    tx_id = update_tx['txID']
                    print(f"  ✓ Транзакция обновления permissions создана")
                    print(f"  TX ID: {tx_id[:16]}...")
                    print()
                    
                    # Подписываем и отправляем транзакцию обновления permissions
                    print("  📝 Подписание транзакции владельцем аккаунта...")
                    
                    # Подготовить для подписи (owner подписывает единолично)
                    update_config = MultisigConfig(
                        required_signatures=1,
                        total_owners=1,
                        owner_addresses=[owner1_address],
                        threshold_weight=1,
                        owner_weights=[1]
                    )
                    
                    # Сохранить raw_data для broadcast
                    contract_data = update_tx.get("raw_data", {})
                    
                    update_transaction = multisig.prepare_transaction_for_signing(
                        raw_data_hex=update_tx["raw_data_hex"],
                        tx_id=tx_id,
                        config=update_config,
                        contract_type="AccountPermissionUpdateContract"
                    )
                    
                    # Добавить contract_data для правильного broadcast
                    update_transaction.contract_data = contract_data
                    
                    # Подписать owner1
                    update_transaction = multisig.sign_transaction(
                        transaction=update_transaction,
                        private_key_hex=owner1_key,
                        signer_address=owner1_address
                    )
                    
                    print(f"  ✓ Подписано владельцем {owner1_address[:10]}...")
                    print()
                    
                    # Отправить в сеть
                    print("  🚀 Отправка транзакции в сеть...")
                    signed_update_tx = multisig.combine_signatures(update_transaction)
                    
                    broadcast_result = await api.broadcast_transaction(signed_update_tx)
                    
                    if broadcast_result.get("result"):
                        print(f"  ✅ Транзакция обновления permissions отправлена!")
                        print(f"  TX ID: {tx_id}")
                        print(f"  🔗 TronScan: https://tronscan.org/#/transaction/{tx_id}")
                        print()
                        print("  ⏳ Ожидание подтверждения (5 сек)...")
                        await asyncio.sleep(5)
                        
                        # Проверить обновление
                        updated_account = await api.get_account(owner1_address)
                        if "active_permission" in updated_account:
                            active_perms = updated_account["active_permission"]
                            for perm in active_perms:
                                if perm.get("permission_name") == "multisig_2_of_3":
                                    print(f"  ✅ Permissions успешно обновлены!")
                                    print(f"     Permission: {perm.get('permission_name')}")
                                    print(f"     Threshold: {perm.get('threshold')}")
                                    print(f"     Keys: {len(perm.get('keys', []))}")
                                    has_multisig = True
                                    break
                            
                            if not has_multisig:
                                print(f"  ⚠️  Permissions возможно еще не применились")
                                print(f"     Проверьте через TronScan через минуту")
                                print()
                                print(f"❌ Permissions не были подтверждены в сети")
                                print(f"   Невозможно продолжить multisig workflow")
                                return
                        print()
                    else:
                        print(f"  ❌ Ошибка отправки: {broadcast_result}")
                        error_msg = broadcast_result.get('Error', broadcast_result.get('message', 'Unknown'))
                        print(f"     Детали: {error_msg}")
                        if "NullPointerException" in str(error_msg):
                            print(f"     Возможная причина: отсутствуют обязательные поля транзакции")
                            print(f"     Проверьте наличие raw_data в signed_update_tx")
                        print()
                else:
                    error_msg = update_tx.get('Error', 'Unknown error')
                    print(f"  ⚠️  Ошибка создания: {error_msg}")
                    if "no OwnerAccount" in error_msg or "account does not exist" in error_msg:
                        print(f"     Аккаунт {owner1_address[:10]}... не активирован")
                        print(f"     Пополните его через faucet или exchanges")
                    elif "owner permission is missed" in error_msg:
                        print(f"     Необходимо указать owner permission при обновлении")
                        print(f"     Это ошибка в коде, обратитесь к разработчику")
                    print()
        except Exception as e:
            print(f"  ❌ Исключение при обновлении permissions: {e}")
            print()
        
        # Убедиться, что permissions установлены
        if not has_multisig:
            print()
            print("=" * 60)
            print("⚠️  Multisig permissions НЕ установлены!")
            print("   Для демонстрации multisig workflow необходимо:")
            print("   1. Пополнить аккаунт до 100+ TRX")
            print("   2. Повторно запустить скрипт для установки permissions")
            print("=" * 60)
            return
        
        # Получить permission_id для multisig
        multisig_permission_id = None
        try:
            account_info = await api.get_account(owner1_address)
            if "active_permission" in account_info:
                for perm in account_info["active_permission"]:
                    if perm.get("permission_name") == "multisig_2_of_3":
                        multisig_permission_id = perm.get("id")
                        print()
                        print("🔑 Найден multisig permission:")
                        print(f"   ID: {multisig_permission_id}")
                        print(f"   Name: {perm.get('permission_name')}")
                        print(f"   Threshold: {perm.get('threshold')}")
                        print()
                        break
        except Exception as e:
            print(f"⚠️  Не удалось получить permission_id: {e}")
        
        if multisig_permission_id is None:
            print()
            print("=" * 60)
            print("⚠️  Multisig permission не найден!")
            print("   Возможно, permissions еще не применились в сети")
            print("   Попробуйте повторить через 1-2 минуты")
            print("=" * 60)
            return
        
        print()
        print("Шаг 1: Создание транзакции (с multisig permissions)")
        print("-" * 40)
        print(f"  ✓ Аккаунт {owner1_address[:10]}... имеет multisig (2/3)")
        print(f"  ✓ Используем permission_id={multisig_permission_id}")
        print("    Любые транзакции требуют 2 подписи из 3")
        print()
        
        recipient = owner3_address  # Send to owner3
        amount = 0.1  # 0.1 TRX
        
        print(f"  Отправка {amount} TRX")
        print(f"  Из: {owner1_address[:10]}... (multisig аккаунт)")
        print(f"  Кому: {recipient[:10]}...")
        print()
        
        try:
            unsigned_tx = await api.create_transaction(
                from_address=owner1_address,
                to_address=recipient,
                amount_trx=amount,
                permission_id=multisig_permission_id
            )
            
            if "txID" not in unsigned_tx:
                print(f"❌ Ошибка: {unsigned_tx}")
                return
            
            tx_id = unsigned_tx["txID"]
            raw_data_hex = unsigned_tx["raw_data_hex"]
            # Сохранить raw_data для broadcast
            contract_data = unsigned_tx.get("raw_data", {})
            
            print(f"  ✓ Транзакция создана: {tx_id[:16]}...")
            print(f"  Эта транзакция использует текущие permissions аккаунта")
            print(f"  (требует 2 из 3 подписей согласно multisig_2_of_3)")
            print()
            
            # Prepare for multisig
            print("Шаг 2: Подготовка для multisig")
            print("-" * 40)
            
            transaction = multisig.prepare_transaction_for_signing(
                raw_data_hex=raw_data_hex,
                tx_id=tx_id,
                config=config,
                contract_type="TransferContract"
            )
            
            # Добавить contract_data для правильного broadcast
            transaction.contract_data = contract_data
            
            print(f"  Требуется подписей: {config.required_signatures}")
            print(f"  Текущих подписей: {transaction.signatures_count}")
            print(f"  Готова к broadcast: {transaction.is_ready_to_broadcast}")
            print()
            print("  💡 Для 2/3 можем использовать любые 2 ключа из 3")
            print("     Демо: используем owner2 + owner3 (без owner1)")
            print()
            
            print("Шаг 3: Сбор подписей от co-signers")
            print("-" * 40)
            print("  Собираем 2 из 3 подписей для выполнения транзакции...")
            print()
            
            # Sign with owner2 (co-signer 1)
            transaction = multisig.sign_transaction(
                transaction=transaction,
                private_key_hex=owner2_key,
                signer_address=owner2_address
            )
            print(f"  ✓ Подписано владельцем 2 (co-signer)")
            print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
            
            # Sign with owner3 (co-signer 2)
            transaction = multisig.sign_transaction(
                transaction=transaction,
                private_key_hex=owner3_key,
                signer_address=owner3_address
            )
            print(f"  ✓ Подписано владельцем 3 (co-signer)")
            print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
            print(f"  Готова к broadcast: {transaction.is_ready_to_broadcast}")
            print()
            
            # Broadcast transaction
            if transaction.is_ready_to_broadcast:
                print("Шаг 4: Отправка транзакции в сеть")
                print("-" * 40)
                print(f"  Отправка с multisig аккаунта {owner1_address[:10]}...")
                print(f"  С подписями от owner2 и owner3")
                print()
                
                signed_tx = multisig.combine_signatures(transaction)
                
                # Добавить visible из оригинальной транзакции
                if "visible" not in signed_tx and "visible" in unsigned_tx:
                    signed_tx["visible"] = unsigned_tx["visible"]
                
                result = await api.broadcast_transaction(signed_tx)
                
                if result.get("result"):
                    print(f"  ✓ Транзакция отправлена!")
                    print(f"  TX ID: {result.get('txid', tx_id)}")
                    print()
                    
                    # Check transaction status
                    print("Шаг 5: Проверка статуса транзакции")
                    print("-" * 40)
                    print("  Ожидание подтверждения (3 сек)...")
                    
                    await asyncio.sleep(3)
                    
                    tx_info = await api.get_transaction_info(tx_id)
                    if tx_info:
                        receipt = tx_info.get('receipt', {})
                        print(f"  ✓ Транзакция найдена")
                        print(f"  Статус: {receipt.get('result', 'UNKNOWN')}")
                        print(f"  Блок: {tx_info.get('blockNumber', 'N/A')}")
                        print(f"  Energy использовано: {receipt.get('energy_usage', 0)}")
                        print(f"  Net использовано: {receipt.get('net_usage', 0)}")
                    else:
                        print(f"  ⚠️  Транзакция еще не подтверждена")
                    print()
                else:
                    print(f"  ❌ Ошибка отправки: {result}")
                    print()
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 60)
    print("📝 Итого:")
    print("  - Используется Account Permission (нативная TRON multisig)")
    print(f"  - Аккаунт {owner1_address[:10]}... настроен на 2/3")
    print("  - Любые транзакции с него требуют 2 подписи из 3")
    print("  - Средства хранятся на owner1_address, не на отдельном адресе")
    print("=" * 60)


def _abi_encode_payout_and_fees(token_hex, nonce, main_recipient_hex, main_amount, fee_recipients_hex, fee_amounts):
    """
    ABI-encode parameters for executePayoutAndFees(
        address token, uint256 nonce, address mainRecipient, uint256 mainAmount,
        address[] feeRecipients, uint256[] feeAmounts
    ).
    All address args: 20-byte hex (no 0x41 prefix), will be right-padded to 32 bytes.
    """
    def addr_to_32(hex_20: str) -> str:
        # 20 bytes = 40 hex chars, right-pad to 32 bytes = 64 hex
        h = hex_20.replace("0x", "").lower()
        if len(h) == 42 and h.startswith("41"):
            h = h[2:]
        return h.zfill(64)

    def u256_to_32(n: int) -> str:
        return ("%064x" % (n % (1 << 256)))

    n = len(fee_recipients_hex)
    head_size = 6 * 32  # 6 slots
    offset_fee_rec = head_size
    offset_fee_amt = head_size + 32 + n * 32

    head = (
        addr_to_32(token_hex)
        + u256_to_32(nonce)
        + addr_to_32(main_recipient_hex)
        + u256_to_32(main_amount)
        + f"{offset_fee_rec:064x}"
        + f"{offset_fee_amt:064x}"
    )
    fee_rec_part = u256_to_32(n) + "".join(addr_to_32(a) for a in fee_recipients_hex)
    fee_amt_part = u256_to_32(n) + "".join(u256_to_32(a) for a in fee_amounts)
    return head + fee_rec_part + fee_amt_part


async def example_multisig_contract_workflow():
    """
    Сценарий проверки: мультиподпись вызова контракта PayoutAndFeesExecutor.
    Строим транзакцию executePayoutAndFees(...), собираем 2/3 подписей, объединяем.
    """
    print("=" * 60)
    print("Multisig + контракт PayoutAndFeesExecutor")
    print("(одна транзакция: основная выплата + комиссии)")
    print("=" * 60)

    if not all([mnemonic1, mnemonic2, mnemonic3]):
        print("Ошибка: нужны MNEMONIC1, MNEMONIC2, MNEMONIC3")
        return

    executor_address = os.getenv("PAYOUT_EXECUTOR_ADDRESS", "").strip()
    if not executor_address:
        print("PAYOUT_EXECUTOR_ADDRESS не задан — только сборка и подписи (без broadcast)")
        print()

    owner1_address, owner1_key = keypair_from_mnemonic(mnemonic1)
    owner2_address, owner2_key = keypair_from_mnemonic(mnemonic2)
    owner3_address, owner3_key = keypair_from_mnemonic(mnemonic3)

    multisig = TronMultisig()
    config = multisig.create_multisig_config(
        required_signatures=2,
        owner_addresses=[owner1_address, owner2_address, owner3_address],
    )

    # Параметры вызова (пример)
    token_contract = os.getenv("TRC20_TOKEN", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
    main_recipient = owner3_address
    main_amount = 1_000_000  # 1 USDT (6 decimals)
    fee_recipients = [owner2_address]
    fee_amounts = [100_000]  # 0.1 USDT
    nonce = int(os.getenv("PAYOUT_NONCE", "0"))

    token_hex = multisig.address_to_hex(token_contract)
    main_recipient_hex = multisig.address_to_hex(main_recipient)
    fee_recipients_hex = [multisig.address_to_hex(a) for a in fee_recipients]

    parameter_hex = _abi_encode_payout_and_fees(
        token_hex, nonce, main_recipient_hex, main_amount, fee_recipients_hex, fee_amounts
    )

    network = os.getenv("TRON_NETWORK", "mainnet")
    print(f"Сеть: {network}")
    print(f"Эскроу (owner1): {owner1_address[:16]}...")
    print(f"Контракт: {executor_address or '(не задан)'}")
    print(f"Основная сумма: {main_amount} (1e6 = 1 USDT) -> {main_recipient[:16]}...")
    print(f"Комиссии: {len(fee_amounts)} получателей")
    print()

    async with TronAPIClient(network=network) as api:
        if not executor_address:
            print("Шаг 1: Пропуск создания транзакции (нет PAYOUT_EXECUTOR_ADDRESS)")
            print("  Задайте адрес контракта и при необходимости PAYOUT_NONCE для реального вызова.")
            print()
            return

        try:
            unsigned_tx = await api.trigger_smart_contract(
                owner_address=owner1_address,
                contract_address=executor_address,
                function_selector="executePayoutAndFees(address,uint256,address,uint256,address[],uint256[])",
                parameter=parameter_hex,
                fee_limit=30_000_000,
            )
        except Exception as e:
            print(f"Ошибка создания транзакции: {e}")
            return

        if "txID" not in unsigned_tx and "transaction" in unsigned_tx:
            unsigned_tx = unsigned_tx["transaction"] or unsigned_tx
        if "txID" not in unsigned_tx:
            print("Ошибка: нет txID в ответе API", unsigned_tx)
            return

        tx_id = unsigned_tx.get("txID") or unsigned_tx.get("txid") or ""
        raw_data_hex = unsigned_tx.get("raw_data_hex") or ""
        if not raw_data_hex:
            print("Ошибка: в ответе API нет raw_data_hex")
            return

        contract_data = unsigned_tx.get("raw_data", {})

        print("Шаг 1: Транзакция создана")
        print(f"  txID: {tx_id[:20]}...")
        print()

        transaction = multisig.prepare_transaction_for_signing(
            raw_data_hex=raw_data_hex,
            tx_id=tx_id,
            config=config,
            contract_type="TriggerSmartContract",
        )
        transaction.contract_data = contract_data

        print("Шаг 2: Сбор 2/3 подписей (owner2, owner3)")
        transaction = multisig.sign_transaction(
            transaction=transaction,
            private_key_hex=owner2_key,
            signer_address=owner2_address,
        )
        print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
        transaction = multisig.sign_transaction(
            transaction=transaction,
            private_key_hex=owner3_key,
            signer_address=owner3_address,
        )
        print(f"  Подписей: {transaction.signatures_count}/{config.required_signatures}")
        print(f"  Готова к broadcast: {transaction.is_ready_to_broadcast}")
        print()

        if not transaction.is_ready_to_broadcast:
            print("Недостаточно подписей для broadcast")
            return

        signed_tx = multisig.combine_signatures(transaction)
        if "visible" not in signed_tx and "visible" in unsigned_tx:
            signed_tx["visible"] = unsigned_tx.get("visible", True)

        print("Шаг 3: Подписанная транзакция собрана")
        if os.getenv("BROADCAST_PAYOUT") == "1":
            result = await api.broadcast_transaction(signed_tx)
            if result.get("result"):
                print(f"  Отправлено. txid: {result.get('txid', tx_id)}")
            else:
                print("  Ошибка broadcast:", result)
        else:
            print("  Broadcast отключен (BROADCAST_PAYOUT=1 для отправки)")

    print()
    print("=" * 60)


def _compile_payout_executor_bytecode():
    """
    Компилирует smart_contracts/PayoutAndFeesExecutor.sol через solc, возвращает bytecode (hex без 0x).
    Возвращает None, если solc не найден или компиляция не удалась.
    """
    contract_path = os.path.join(project_root, "smart_contracts", "PayoutAndFeesExecutor.sol")
    if not os.path.isfile(contract_path):
        print(f"Файл контракта не найден: {contract_path}")
        return None
    out_dir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            ["solc", "--bin", "--optimize", "-o", out_dir, contract_path],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30,
        )
        if result.returncode != 0:
            print("solc ошибка:", result.stderr or result.stdout)
            return None
        bin_path = os.path.join(out_dir, "PayoutAndFeesExecutor.bin")
        if not os.path.isfile(bin_path):
            print("solc не создал PayoutAndFeesExecutor.bin")
            return None
        with open(bin_path, "r", encoding="utf-8") as f:
            bytecode = f.read().strip().replace("0x", "")
        return bytecode
    except FileNotFoundError:
        print("solc не найден. Установите Solidity 0.5.x и добавьте в PATH (например: solc-select install 0.5.10).")
        return None
    except subprocess.TimeoutExpired:
        print("Таймаут компиляции solc")
        return None
    finally:
        try:
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)
        except Exception:
            pass


async def example_multisig_contract_deploy():
    """
    Деплой контракта PayoutAndFeesExecutor в сеть.
    Компилирует .sol через solc, создаёт транзакцию деплоя, подписывает ключом MNEMONIC1, отправляет в сеть.
    """
    print("=" * 60)
    print("Деплой контракта PayoutAndFeesExecutor")
    print("=" * 60)

    if not mnemonic1:
        print("Ошибка: задайте MNEMONIC1 (от имени этого адреса будет задеплоен контракт)")
        return

    bytecode = _compile_payout_executor_bytecode()
    if not bytecode:
        return

    owner1_address, owner1_key = keypair_from_mnemonic(mnemonic1)
    network = os.getenv("TRON_NETWORK", "shasta")

    print(f"Сеть: {network}")
    print(f"Деплой от: {owner1_address[:20]}...")
    print()

    async with TronAPIClient(network=network) as api:
        try:
            resp = await api._post(
                "/wallet/deploycontract",
                {
                    "owner_address": owner1_address,
                    "bytecode": bytecode,
                    "name": "PayoutAndFeesExecutor",
                    "fee_limit": 100_000_000,
                    "visible": True,
                },
            )
        except Exception as e:
            print(f"Ошибка API deploycontract: {e}")
            return

        tx = resp.get("transaction") if isinstance(resp.get("transaction"), dict) else resp
        if not tx or "txID" not in tx:
            print("Ответ API без транзакции:", resp)
            return

        tx_id = tx.get("txID") or tx.get("txid") or ""
        raw_data_hex = tx.get("raw_data_hex") or ""
        if not raw_data_hex:
            print("В ответе нет raw_data_hex")
            return

        try:
            from tronpy.keys import PrivateKey as TronPrivateKey
            tx_id_bytes = bytes.fromhex(tx_id)
            private_key_bytes = bytes.fromhex(owner1_key)
            tron_key = TronPrivateKey(private_key_bytes)
            signature_bytes = tron_key.sign_msg_hash(tx_id_bytes)
            signature_hex = signature_bytes.hex()
        except Exception as e:
            print(f"Ошибка подписи: {e}")
            return

        signed_tx = {
            "txID": tx_id,
            "raw_data_hex": raw_data_hex,
            "signature": [signature_hex],
        }
        if tx.get("raw_data"):
            signed_tx["raw_data"] = tx["raw_data"]

        print("Транзакция подписана, отправка в сеть...")
        result = await api.broadcast_transaction(signed_tx)
        if not result.get("result"):
            print("Ошибка broadcast:", result)
            return

        txid = result.get("txid") or tx_id
        print(f"Транзакция отправлена: {txid[:24]}...")
        print("Ожидание подтверждения (5 сек)...")
        await asyncio.sleep(5)

        info = await api.get_transaction_info(txid)
        if not info:
            print("Не удалось получить transaction info")
            print("Сохраните txid и проверьте контракт в эксплорере.")
            print()
            return

        contract_addr = info.get("contract_address")
        if contract_addr:
            from services.tron.multisig import TronMultisig
            base58_addr = TronMultisig.hex_to_address(contract_addr) if contract_addr.startswith("41") else contract_addr
            print()
            print("Адрес задеплоенного контракта (Base58):", base58_addr)
            print("Адрес (hex):", contract_addr)
            print()
            print("Для эскроу задайте: payout_executor_address =", base58_addr)
        else:
            receipt = info.get("receipt", {})
            print("Transaction info:", info.get("receipt"))
            if receipt.get("result") == "SUCCESS":
                print("Деплой успешен, но contract_address не в ответе. Проверьте tx в эксплорере.")
        print("=" * 60)


async def check_balances():
    """Check balances for address from MNEMONIC1"""
    if not mnemonic1:
        print("Please set MNEMONIC1 environment variable")
        return
    
    _owner1_addr, _owner1_key = keypair_from_mnemonic(mnemonic1)
    print(f"Address: {_owner1_addr}")
    print(f"Private Key: {_owner1_key[:16]}...")
    print()
    
    # Check balance on mainnet
    print("Checking balance on TRON Mainnet...")
    async with TronAPIClient(network="mainnet") as api:
        try:
            # Get TRX balance
            balance = await api.get_balance(_owner1_addr)
            print(f"TRX Balance: {balance:.6f} TRX")
            
            # Get USDT balance (TRC20)
            usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
            usdt_balance = await api.get_trc20_balance(_owner1_addr, usdt_contract, decimals=6)
            print(f"USDT Balance: {usdt_balance:.6f} USDT")
            
            # Get account info
            account = await api.get_account(_owner1_addr)
            if account:
                print(f"Account exists: Yes")
                bandwidth = account.get('free_net_usage', 0)
                print(f"Bandwidth: {bandwidth}")
            else:
                print(f"Account exists: No")
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Main function"""
    print("TRON Multisig Demo\n")
    
    # Check what to run
    mode = os.getenv("MODE", "multisig")  # balance or multisig
    
    if mode == "multisig":
        await example_full_multisig_workflow()
    elif mode == "multisig-contract":
        await example_multisig_contract_workflow()
    elif mode == "multisig-contract-deploy":
        await example_multisig_contract_deploy()
    else:
        await check_balances()
    
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())