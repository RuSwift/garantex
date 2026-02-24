"""
PayoutAndFeesExecutor contract integration: ABI encoding and nonce read.
"""
import os
from typing import List, Optional

from services.tron.multisig import TronMultisig


def get_executor_address() -> Optional[str]:
    """Return PAYOUT_EXECUTOR_ADDRESS from env or None."""
    return (os.getenv("PAYOUT_EXECUTOR_ADDRESS") or "").strip() or None


def _addr_to_32(hex_addr: str) -> str:
    """ABI: 20-byte address right-padded to 32 bytes (64 hex)."""
    h = (hex_addr or "").replace("0x", "").lower()
    if len(h) == 42 and h.startswith("41"):
        h = h[2:]
    return h.zfill(64)


def _u256_to_32(n: int) -> str:
    """ABI: uint256 as 32 bytes hex."""
    return "%064x" % (n % (1 << 256))


def abi_encode_execute_payout_and_fees(
    token_hex: str,
    nonce: int,
    main_recipient_hex: str,
    main_amount: int,
    fee_recipients_hex: List[str],
    fee_amounts: List[int],
) -> str:
    """
    ABI-encode parameters for executePayoutAndFees(
        address token, uint256 nonce, address mainRecipient, uint256 mainAmount,
        address[] feeRecipients, uint256[] feeAmounts
    ).
    Addresses: TRON hex (0x41 + 20 bytes) from TronMultisig.address_to_hex.
    """
    n = len(fee_recipients_hex)
    if n != len(fee_amounts):
        raise ValueError("fee_recipients and fee_amounts length mismatch")
    head_size = 6 * 32
    offset_fee_rec = head_size
    offset_fee_amt = head_size + 32 + n * 32

    head = (
        _addr_to_32(token_hex)
        + _u256_to_32(nonce)
        + _addr_to_32(main_recipient_hex)
        + _u256_to_32(main_amount)
        + "%064x" % offset_fee_rec
        + "%064x" % offset_fee_amt
    )
    fee_rec_part = _u256_to_32(n) + "".join(_addr_to_32(a) for a in fee_recipients_hex)
    fee_amt_part = _u256_to_32(n) + "".join(_u256_to_32(a) for a in fee_amounts)
    return head + fee_rec_part + fee_amt_part


async def get_executor_nonce(api_client, executor_address: str, escrow_address: str) -> int:
    """
    Read nonces(escrow_address) from PayoutAndFeesExecutor contract.
    api_client: TronAPIClient instance (async context).
    """
    multisig = TronMultisig()
    escrow_hex = multisig.address_to_hex(escrow_address)
    param = _addr_to_32(escrow_hex)

    result = await api_client._post(
        "/wallet/triggersmartcontract",
        {
            "owner_address": escrow_address,
            "contract_address": executor_address,
            "function_selector": "nonces(address)",
            "parameter": param,
            "visible": True,
        },
    )
    if result.get("constant_result") and len(result["constant_result"]) > 0:
        return int(result["constant_result"][0], 16)
    return 0
