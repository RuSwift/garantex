"""
Test script for multisig API endpoints
"""
import asyncio
import os
from services.tron.api_client import TronAPIClient
from services.tron.utils import keypair_from_mnemonic

async def test_api():
    """Test the multisig API workflow"""
    
    # Get mnemonics from env
    mnemonic1 = os.getenv("MNEMONIC1")
    mnemonic2 = os.getenv("MNEMONIC2")
    mnemonic3 = os.getenv("MNEMONIC3")
    
    if not all([mnemonic1, mnemonic2, mnemonic3]):
        print("❌ Please set MNEMONIC1, MNEMONIC2, MNEMONIC3 environment variables")
        return
    
    # Generate keypairs
    owner1_address, owner1_key = keypair_from_mnemonic(mnemonic1)
    owner2_address, owner2_key = keypair_from_mnemonic(mnemonic2)
    owner3_address, owner3_key = keypair_from_mnemonic(mnemonic3)
    
    print("=" * 60)
    print("Testing Multisig API Workflow")
    print("=" * 60)
    print()
    print(f"Owner1: {owner1_address}")
    print(f"Owner2: {owner2_address}")
    print(f"Owner3: {owner3_address}")
    print()
    
    # Test 1: Check permissions
    print("Test 1: Checking permissions for Owner1...")
    print("-" * 60)
    
    async with TronAPIClient(network="mainnet") as api:
        try:
            account_info = await api.get_account(owner1_address)
            
            if not account_info:
                print("❌ Account not found or not activated")
                return
            
            print(f"✓ Account found")
            
            if "active_permission" in account_info:
                active_permissions = account_info["active_permission"]
                print(f"✓ Active permissions found: {len(active_permissions)}")
                
                for perm in active_permissions:
                    permission_id = perm.get("id")
                    permission_name = perm.get("permission_name", "active")
                    threshold = perm.get("threshold", 1)
                    keys = perm.get("keys", [])
                    
                    print(f"  Permission ID: {permission_id}")
                    print(f"  Name: {permission_name}")
                    print(f"  Threshold: {threshold}")
                    print(f"  Keys: {len(keys)}")
                    
                    if permission_name == "multisig_2_of_3":
                        print(f"  ✓ Multisig permission found!")
                        print()
                        print(f"  Keys:")
                        for key in keys:
                            addr = key.get("address", "")
                            weight = key.get("weight", 0)
                            print(f"    - {addr} (weight: {weight})")
                        print()
            else:
                print("⚠ No active_permission found")
            
            print()
            
            # Test 2: Check balance
            print("Test 2: Checking balance...")
            print("-" * 60)
            
            balance = await api.get_balance(owner1_address)
            print(f"Balance: {balance:.6f} TRX")
            
            if balance < 1:
                print("⚠ Warning: Low balance. Need at least 1 TRX for testing")
            
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 60)
    print("✅ API tests completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_api())


