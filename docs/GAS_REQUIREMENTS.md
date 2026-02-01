# Gas Requirements

This document explains gas requirements for PayKit operations across different networks.

## Overview

PayKit uses Circle's Developer-Controlled Wallets, which handle gas fees automatically for most operations. However, some operations (particularly cross-chain transfers) may require native gas tokens on your wallet.

## Gas by Operation Type

| Operation | Gas Required | Who Pays |
|-----------|--------------|----------|
| Direct USDC Transfer | Native token | Circle (gasless) |
| x402 API Payment | Native token | Circle (gasless) |
| CCTP Standard Transfer | Native token (source) | Circle (gasless) |
| CCTP Fast Transfer | Native token (both chains) | You (destination only) |
| Smart Contract Execution | Native token | Circle (gasless) |

## Gasless Transfers (Default)

Most operations are **gasless** - Circle sponsors the gas fees:

```python
# These operations don't require you to have gas
await client.pay(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("10.00")
)  # Circle pays gas
```

## Cross-Chain Gas Requirements

For CCTP **fast transfers**, your wallet needs gas on the **destination chain** to mint the USDC.

### Minimum Gas Recommendations

| Network | Token | Min Balance | Typical Cost |
|---------|-------|-------------|--------------|
| Ethereum Mainnet | ETH | 0.02 ETH | 0.005-0.015 ETH |
| Ethereum Sepolia | ETH | 0.02 ETH | 0.001-0.005 ETH |
| Base Mainnet | ETH | 0.001 ETH | 0.0001-0.0005 ETH |
| Base Sepolia | ETH | 0.001 ETH | 0.0001-0.0003 ETH |
| Arbitrum Mainnet | ETH | 0.001 ETH | 0.0001-0.0005 ETH |
| Arbitrum Sepolia | ETH | 0.001 ETH | 0.0001-0.0003 ETH |
| Polygon Mainnet | MATIC | 0.1 MATIC | 0.01-0.05 MATIC |
| Polygon Amoy | MATIC | 0.1 MATIC | 0.01-0.03 MATIC |
| Avalanche Mainnet | AVAX | 0.1 AVAX | 0.01-0.05 AVAX |
| Avalanche Fuji | AVAX | 0.1 AVAX | 0.01-0.03 AVAX |
| Arc Testnet | ETH | 0.001 ETH | 0.0001-0.0003 ETH |

## Checking Gas Balance

```python
# Get wallet info
wallet = await client.wallet.get_wallet(wallet_id)

# Check balances (includes gas token)
balances = client.wallet.get_balances(wallet_id)
for b in balances:
    print(f"{b.token.symbol}: {b.amount}")
```

## Funding Wallets with Gas

### Testnets

Use faucets to get testnet tokens:

| Network | Faucet |
|---------|--------|
| Ethereum Sepolia | [sepoliafaucet.com](https://sepoliafaucet.com) |
| Base Sepolia | [faucet.base.org](https://faucet.base.org) |
| Arbitrum Sepolia | [faucet.arbitrum.io](https://faucet.arbitrum.io) |
| Polygon Amoy | [faucet.polygon.technology](https://faucet.polygon.technology) |
| Avalanche Fuji | [faucet.avax.network](https://faucet.avax.network) |

### Mainnets

Transfer native tokens to your wallet address from an exchange or another wallet.

## Handling Insufficient Gas

```python
from paykit import PayKitError

try:
    result = await client.pay(
        wallet_id=wallet.id,
        recipient="0x...",
        amount=Decimal("100.00"),
        destination_chain=Network.BASE
    )
except PayKitError as e:
    if "gas" in str(e).lower():
        print("Insufficient gas on destination chain")
        print(f"Fund wallet with native gas token")
```

## Fallback to Standard Transfer

If your wallet lacks gas on the destination chain, use standard CCTP transfer:

```python
# Standard transfer doesn't require gas on destination
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("100.00"),
    destination_chain=Network.BASE,
    use_fast_transfer=False  # Uses standard transfer
)
# Takes 13-19 minutes but doesn't require destination gas
```

## Gas Estimation

```python
# Simulate to check if gas is available
simulation = await client.simulate(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("100.00"),
    destination_chain=Network.BASE
)

if not simulation.would_succeed:
    if "gas" in simulation.reason.lower():
        print("Need gas on destination chain")
```

## Fee Levels

For operations where you control gas, you can set the fee level:

```python
from paykit import FeeLevel

result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("10.00"),
    fee_level=FeeLevel.HIGH  # Faster confirmation
)
```

| Fee Level | Speed | Cost |
|-----------|-------|------|
| `LOW` | Slower | Cheapest |
| `MEDIUM` | Normal | Default |
| `HIGH` | Fastest | Most expensive |

## Best Practices

1. **Keep gas buffers**: Maintain 2-3x the minimum gas on frequently-used chains

2. **Monitor balances**: Set up alerts when gas drops below threshold

3. **Use standard transfer for large amounts**: More reliable, no gas needed on destination

4. **Pre-fund destination wallets**: If doing many cross-chain transfers, fund destination wallets upfront

```python
# Check gas before cross-chain transfer
async def safe_cross_chain_transfer(wallet_id, recipient, amount, dest_chain):
    # Check if we have gas on destination
    dest_wallet = await get_wallet_on_chain(dest_chain)
    gas_balance = await get_gas_balance(dest_wallet)
    
    if gas_balance < MIN_GAS[dest_chain]:
        # Fall back to standard transfer
        use_fast = False
    else:
        use_fast = True
    
    return await client.pay(
        wallet_id=wallet_id,
        recipient=recipient,
        amount=amount,
        destination_chain=dest_chain,
        use_fast_transfer=use_fast
    )
```
