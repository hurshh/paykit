#!/usr/bin/env python3
"""
Quick test script to verify PayKit providers are working.

Usage:
    # Test Circle (default)
    CIRCLE_API_KEY=xxx python scripts/test_providers.py
    
    # Test Coinbase
    CDP_API_KEY_ID=xxx CDP_API_KEY_SECRET=xxx CDP_WALLET_SECRET=xxx \
        python scripts/test_providers.py --provider coinbase
"""

import asyncio
import argparse
import os
import sys
from decimal import Decimal

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def test_circle_provider():
    """Test Circle provider functionality."""
    print("\n" + "=" * 60)
    print("Testing Circle Provider")
    print("=" * 60)
    
    # Check for API key
    api_key = os.environ.get("CIRCLE_API_KEY")
    if not api_key:
        print("❌ CIRCLE_API_KEY not set")
        print("   Set it with: export CIRCLE_API_KEY='your-api-key'")
        return False
    
    print(f"✓ API Key found: {api_key[:8]}...")
    
    try:
        from paykit import PayKit, Network
        
        # Initialize client
        print("\n1. Initializing PayKit client...")
        client = PayKit(network=Network.ARC_TESTNET)
        print("   ✓ Client initialized")
        
        # List wallet sets
        print("\n2. Listing wallet sets...")
        wallet_sets = client.wallet.list_wallet_sets()
        print(f"   ✓ Found {len(wallet_sets)} wallet sets")
        for ws in wallet_sets[:3]:
            print(f"      - {ws.name} ({ws.id})")
        
        # List wallets
        print("\n3. Listing wallets...")
        wallets = client.wallet.list_wallets()
        print(f"   ✓ Found {len(wallets)} wallets")
        for w in wallets[:3]:
            print(f"      - {w.address[:20]}... ({w.blockchain})")
        
        # Check balance (if wallets exist)
        if wallets:
            print("\n4. Checking balance...")
            wallet = wallets[0]
            balance = client.wallet.get_usdc_balance_amount(wallet.id)
            print(f"   ✓ Balance: {balance} USDC")
        
        print("\n" + "=" * 60)
        print("✓ Circle Provider: ALL TESTS PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_coinbase_provider():
    """Test Coinbase provider functionality."""
    print("\n" + "=" * 60)
    print("Testing Coinbase Provider")
    print("=" * 60)
    
    # Check for API keys
    api_key_id = os.environ.get("CDP_API_KEY_ID")
    api_key_secret = os.environ.get("CDP_API_KEY_SECRET")
    wallet_secret = os.environ.get("CDP_WALLET_SECRET")
    
    if not all([api_key_id, api_key_secret, wallet_secret]):
        print("❌ Coinbase credentials not set")
        print("   Set them with:")
        print("     export CDP_API_KEY_ID='your-api-key-id'")
        print("     export CDP_API_KEY_SECRET='your-api-key-secret'")
        print("     export CDP_WALLET_SECRET='your-wallet-secret'")
        return False
    
    print(f"✓ API Key ID found: {api_key_id[:8]}...")
    
    try:
        from paykit.providers import CoinbaseProvider, CoinbaseConfig
        
        # Initialize provider
        print("\n1. Initializing Coinbase provider...")
        config = CoinbaseConfig(
            api_key=api_key_id,
            api_secret=api_key_secret,
            wallet_secret=wallet_secret,
        )
        provider = CoinbaseProvider(config)
        print("   ✓ Provider initialized")
        
        # Create wallet set
        print("\n2. Creating wallet set...")
        wallet_set = await provider.create_wallet_set("test-set")
        print(f"   ✓ Wallet set created: {wallet_set.id}")
        
        # Create wallet
        print("\n3. Creating wallet...")
        wallet = await provider.create_wallet(
            wallet_set_id=wallet_set.id,
            blockchain="BASE-SEPOLIA",
            name="test-wallet"
        )
        print(f"   ✓ Wallet created: {wallet.address}")
        
        # Get balances
        print("\n4. Getting balances...")
        balances = await provider.get_balances(wallet.id)
        print(f"   ✓ Found {len(balances)} token balances")
        for b in balances:
            print(f"      - {b.token_symbol}: {b.amount}")
        
        print("\n" + "=" * 60)
        print("✓ Coinbase Provider: ALL TESTS PASSED")
        print("=" * 60)
        return True
        
    except ImportError:
        print("❌ cdp-sdk not installed")
        print("   Install with: pip install paykit[coinbase]")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_provider_abstraction():
    """Test the provider factory."""
    print("\n" + "=" * 60)
    print("Testing Provider Factory")
    print("=" * 60)
    
    try:
        from paykit.providers import get_provider, list_providers, ProviderType
        
        print("\n1. Listing available providers...")
        providers = list_providers()
        print(f"   ✓ Available: {[p.value for p in providers]}")
        
        print("\n2. Testing provider factory...")
        
        # Test Circle (if credentials available)
        if os.environ.get("CIRCLE_API_KEY"):
            try:
                provider = get_provider(ProviderType.CIRCLE)
                print(f"   ✓ Circle provider: {provider.provider_type.value}")
            except Exception as e:
                print(f"   ❌ Circle: {e}")
        
        print("\n" + "=" * 60)
        print("✓ Provider Factory: TESTS PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test PayKit providers")
    parser.add_argument(
        "--provider",
        choices=["circle", "coinbase", "all"],
        default="circle",
        help="Which provider to test"
    )
    args = parser.parse_args()
    
    print("\n🔧 PayKit Provider Test Suite")
    print("================================\n")
    
    results = []
    
    # Test provider factory
    results.append(("Factory", await test_provider_abstraction()))
    
    # Test specific provider
    if args.provider in ("circle", "all"):
        results.append(("Circle", await test_circle_provider()))
    
    if args.provider in ("coinbase", "all"):
        results.append(("Coinbase", await test_coinbase_provider()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
