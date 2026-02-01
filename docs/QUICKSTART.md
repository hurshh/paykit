# PayKit Quickstart

Get your AI agent making payments in 5 minutes.

## Step 1: Install

```bash
pip install paykit
```

## Step 2: Get API Key

1. Go to [Circle Console](https://console.circle.com)
2. Create an account
3. Navigate to **API Keys**
4. Create a new API key
5. Copy the key

## Step 3: Set Environment

```bash
export CIRCLE_API_KEY="your-api-key-here"
```

Or create a `.env` file:

```
CIRCLE_API_KEY=your-api-key-here
```

## Step 4: Create Wallet

```python
import asyncio
from paykit import PayKit

async def setup():
    client = PayKit()
    
    # Create a wallet for your agent
    wallet_set, wallet = await client.create_agent_wallet("my-agent")
    
    print(f"Wallet Address: {wallet.address}")
    print(f"Wallet ID: {wallet.id}")
    
    # Save these for later!
    return wallet

asyncio.run(setup())
```

## Step 5: Fund Wallet

Send USDC to your wallet address on the Arc testnet.

**Get testnet USDC:**
- Use Circle's testnet faucet
- Or bridge from another testnet

## Step 6: Add Safety Guards

```python
from decimal import Decimal

async def add_guards(client, wallet_id):
    # Limit daily spending to $100
    await client.add_budget_guard(
        wallet_id,
        daily_limit=Decimal("100.00")
    )
    
    # Limit to 10 transactions per hour
    await client.add_rate_limit_guard(
        wallet_id,
        max_per_hour=10
    )
    
    print("Guards added!")

asyncio.run(add_guards(PayKit(), "your-wallet-id"))
```

## Step 7: Make a Payment

```python
from decimal import Decimal
from paykit import PayKit

async def pay():
    client = PayKit()
    
    result = await client.pay(
        wallet_id="your-wallet-id",
        recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
        amount=Decimal("1.00"),
        purpose="Test payment"
    )
    
    if result.success:
        print(f"Payment successful!")
        print(f"Transaction: {result.blockchain_tx}")
    else:
        print(f"Payment failed: {result.error}")

asyncio.run(pay())
```

## Complete Example

```python
import asyncio
from decimal import Decimal
from paykit import PayKit, Network

async def main():
    # Initialize
    client = PayKit(network=Network.ARC_TESTNET)
    
    # Create wallet
    wallet_set, wallet = await client.create_agent_wallet("quickstart-agent")
    print(f"Created wallet: {wallet.address}")
    
    # Add safety guards
    await client.add_budget_guard(wallet.id, daily_limit=Decimal("100.00"))
    await client.add_rate_limit_guard(wallet.id, max_per_hour=10)
    print("Guards configured")
    
    # Check balance
    balance = await client.get_balance(wallet.id)
    print(f"Balance: {balance} USDC")
    
    if balance > 0:
        # Make payment
        result = await client.pay(
            wallet_id=wallet.id,
            recipient="0x000000000000000000000000000000000000dEaD",
            amount=Decimal("0.01"),
            purpose="Quickstart test"
        )
        print(f"Payment: {result.status}")
    else:
        print("Fund your wallet to make payments!")
        print(f"Address: {wallet.address}")

asyncio.run(main())
```

## Next Steps

- [Full SDK Usage Guide](SDK_USAGE_GUIDE.md)
- [API Reference](API_REFERENCE.md)
- [Safety Guards](SDK_USAGE_GUIDE.md#safety-guards)
- [Cross-Chain Transfers](CCTP_USAGE.md)

## Troubleshooting

### "CIRCLE_API_KEY not set"

Set the environment variable:
```bash
export CIRCLE_API_KEY="your-key"
```

### "Entity secret invalid"

Delete `ENTITY_SECRET` from your `.env` and restart. A new one will be generated.

### "Insufficient balance"

Fund your wallet with USDC. Check the balance:
```python
balance = await client.get_balance(wallet.id)
```

### "Guard blocked payment"

Your safety guards are working! Check limits:
```python
guards = await client.list_guards(wallet.id)
```
