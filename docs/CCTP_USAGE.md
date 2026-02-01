# Cross-Chain Transfers with CCTP

PayKit uses Circle's **Cross-Chain Transfer Protocol (CCTP)** to move USDC between blockchains without bridges.

## Overview

CCTP is a permissionless protocol that enables native USDC transfers between supported blockchains. Unlike bridges that use wrapped tokens, CCTP burns USDC on the source chain and mints native USDC on the destination chain.

```
Source Chain                 Circle                  Destination Chain
─────────────               ──────                  ─────────────────
1. Burn USDC      →    2. Attestation    →    3. Mint USDC
   (destroyed)            (proof)                (created fresh)
```

## Supported Chains

| Chain | Testnet | Mainnet |
|-------|---------|---------|
| Ethereum | ETH-SEPOLIA | ETH |
| Base | BASE-SEPOLIA | BASE |
| Arbitrum | ARB-SEPOLIA | ARB |
| Polygon | MATIC-AMOY | MATIC |
| Avalanche | AVAX-FUJI | AVAX |
| Arc | ARC-TESTNET | - |

## Basic Usage

### Simple Cross-Chain Payment

```python
from paykit import PayKit, Network
from decimal import Decimal

client = PayKit()

# Transfer from Arc to Base
result = await client.pay(
    wallet_id="your-wallet-id",
    recipient="0xRecipientOnBase...",
    amount=Decimal("100.00"),
    destination_chain=Network.BASE_SEPOLIA
)

if result.success:
    print(f"Transfer complete: {result.blockchain_tx}")
```

### Specifying Source and Destination

```python
# Create wallets on different chains
arc_wallet = await client.create_wallet(
    blockchain=Network.ARC_TESTNET,
    name="arc-wallet"
)

base_wallet = await client.create_wallet(
    blockchain=Network.BASE_SEPOLIA,
    name="base-wallet"
)

# Transfer from Arc to Base
result = await client.pay(
    wallet_id=arc_wallet.id,  # Source on Arc
    recipient=base_wallet.address,  # Destination on Base
    amount=Decimal("50.00"),
    destination_chain=Network.BASE_SEPOLIA
)
```

## Transfer Modes

CCTP supports two transfer modes:

### Fast Transfer (Default)

**Time:** 2-5 seconds
**How it works:** Agent-side minting

```python
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("10.00"),
    destination_chain=Network.BASE_SEPOLIA,
    # Fast transfer is the default
)

print(result.metadata.get("transfer_mode"))
# Output: "fast"
```

**Requirements:**
- Source wallet needs USDC for the transfer
- Destination wallet needs native gas token (ETH, MATIC, etc.) to call `receiveMessage()`

### Standard Transfer

**Time:** 13-19 minutes
**How it works:** Automatic attestation and minting

```python
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("1000.00"),
    destination_chain=Network.BASE_SEPOLIA,
    use_fast_transfer=False  # Use standard mode
)
```

**When to use:**
- Larger transfers (>$1000)
- No gas available on destination chain
- When speed isn't critical

## Technical Flow

### Fast Transfer Flow

```
1. approve()      - Approve TokenMessenger to spend USDC
2. depositForBurn() - Burn USDC on source chain
3. Poll Iris API  - Wait for attestation (Circle signs the burn)
4. receiveMessage() - Mint USDC on destination chain (agent calls this)
```

### Standard Transfer Flow

```
1. approve()      - Approve TokenMessenger to spend USDC
2. depositForBurn() - Burn USDC on source chain
3. Wait           - Circle automatically processes the attestation
4. Auto-mint      - USDC appears on destination chain
```

## Gas Requirements

For fast transfers, your wallet needs gas on the destination chain to call `receiveMessage()`.

| Destination Chain | Gas Token | Approximate Cost |
|------------------|-----------|------------------|
| Ethereum | ETH | ~0.01 ETH |
| Base | ETH | ~0.0001 ETH |
| Arbitrum | ETH | ~0.0001 ETH |
| Polygon | MATIC | ~0.01 MATIC |
| Avalanche | AVAX | ~0.01 AVAX |
| Arc Testnet | ETH | ~0.0001 ETH |

See [GAS_REQUIREMENTS.md](GAS_REQUIREMENTS.md) for detailed information.

## Checking Transfer Status

```python
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("100.00"),
    destination_chain=Network.BASE_SEPOLIA
)

# Check status
print(f"Status: {result.status}")
print(f"Source TX: {result.blockchain_tx}")
print(f"Transfer Mode: {result.metadata.get('transfer_mode')}")

# For pending transfers, sync later
if result.status == "pending":
    updated = await client.sync_transaction(result.transaction_id)
    print(f"Updated status: {updated.status}")
```

## Error Handling

```python
from paykit import PayKitError, CrosschainError

try:
    result = await client.pay(
        wallet_id=wallet.id,
        recipient="0x...",
        amount=Decimal("100.00"),
        destination_chain=Network.BASE_SEPOLIA
    )
except CrosschainError as e:
    print(f"Cross-chain transfer failed: {e}")
    print(f"Details: {e.details}")
except PayKitError as e:
    print(f"Payment failed: {e}")
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Insufficient balance` | Not enough USDC | Fund the wallet |
| `Attestation timeout` | Circle attestation delayed | Retry or use standard mode |
| `Gas required on destination` | No gas for minting | Fund destination with gas token |
| `Unsupported chain pair` | Chain not supported | Check supported chains above |

## Simulating Cross-Chain Transfers

```python
simulation = await client.simulate(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("100.00"),
    destination_chain=Network.BASE_SEPOLIA
)

if simulation.would_succeed:
    print(f"Estimated fee: {simulation.estimated_fee}")
    print(f"Method: {simulation.payment_method}")  # CROSS_CHAIN
else:
    print(f"Would fail: {simulation.reason}")
```

## Best Practices

### 1. Check Gas Before Fast Transfers

```python
# Ensure destination wallet has gas
dest_gas = await check_gas_balance(dest_wallet)
if dest_gas < MIN_GAS_REQUIRED:
    # Use standard transfer instead
    use_fast = False
```

### 2. Use Appropriate Mode for Amount

```python
amount = Decimal("5000.00")

# Large amounts → standard transfer (more reliable)
# Small amounts → fast transfer (faster)
use_fast = amount < Decimal("1000.00")

result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=amount,
    destination_chain=Network.BASE_SEPOLIA,
    use_fast_transfer=use_fast
)
```

### 3. Handle Timeouts Gracefully

```python
try:
    result = await client.pay(
        wallet_id=wallet.id,
        recipient="0x...",
        amount=Decimal("100.00"),
        destination_chain=Network.BASE_SEPOLIA,
        timeout_seconds=120.0  # 2 minute timeout
    )
except TransactionTimeoutError:
    # Transfer may still complete
    # Check status later
    pass
```

## Resources

- [Circle CCTP Documentation](https://developers.circle.com/stablecoins/cctp)
- [CCTP Smart Contracts](https://github.com/circlefin/cctp)
- [Supported Networks](CCTP_NETWORKS.md)
- [Gas Requirements](GAS_REQUIREMENTS.md)
