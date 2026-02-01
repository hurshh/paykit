# PayKit SDK Usage Guide

Practical patterns and examples for integrating PayKit into your AI agents.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Wallet Management](#wallet-management)
3. [Making Payments](#making-payments)
4. [Safety Guards](#safety-guards)
5. [Multi-Agent Patterns](#multi-agent-patterns)
6. [Integration Examples](#integration-examples)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation

```bash
pip install paykit
```

### Environment Setup

Create a `.env` file:

```bash
# Required
CIRCLE_API_KEY=your-circle-api-key

# Optional (auto-generated if missing)
ENTITY_SECRET=your-entity-secret

# Configuration
PAYKIT_NETWORK=ARC-TESTNET
PAYKIT_STORAGE_BACKEND=memory
PAYKIT_LOG_LEVEL=INFO
```

### First Payment

```python
import asyncio
from decimal import Decimal
from paykit import PayKit

async def main():
    # Initialize
    client = PayKit()
    
    # Create wallet
    wallet_set, wallet = await client.create_agent_wallet("my-first-agent")
    print(f"Created wallet: {wallet.address}")
    
    # Fund the wallet (transfer USDC to wallet.address)
    # Then make a payment
    result = await client.pay(
        wallet_id=wallet.id,
        recipient="0x...",
        amount=Decimal("1.00")
    )
    print(f"Payment status: {result.status}")

asyncio.run(main())
```

---

## Wallet Management

### Agent Wallets vs User Wallets

```python
# Agent wallets - for autonomous AI agents
wallet_set, wallet = await client.create_agent_wallet(
    agent_name="trading-bot-v1"
)
# Creates: wallet set "agent-trading-bot-v1" with one wallet

# User wallets - for end users of your application
wallet_set, wallet = await client.create_user_wallet(
    user_id="user-12345"
)
# Creates: wallet set "user-user-12345" with one wallet
```

### Multiple Wallets per Agent

```python
# Create a wallet set for an agent swarm
wallet_set = await client.create_wallet_set(name="research-swarm")

# Create multiple wallets in the set
from paykit import Network

eth_wallet = await client.create_wallet(
    wallet_set_id=wallet_set.id,
    blockchain=Network.ETH_SEPOLIA,
    name="eth-wallet"
)

base_wallet = await client.create_wallet(
    wallet_set_id=wallet_set.id,
    blockchain=Network.BASE_SEPOLIA,
    name="base-wallet"
)
```

### Checking Balances

```python
# Simple balance check
balance = await client.get_balance(wallet.id)
print(f"USDC Balance: {balance}")

# Detailed balance info
from paykit import Balance
balances = client.wallet.get_balances(wallet.id)
for b in balances:
    print(f"{b.token.symbol}: {b.amount}")
```

### Wallet Discovery

```python
# List all wallets
wallets = client.wallet.list_wallets()

# Filter by wallet set
wallets = client.wallet.list_wallets(wallet_set_id="...")

# Find wallet by address
wallet = next((w for w in wallets if w.address == "0x..."), None)
```

---

## Making Payments

### Direct Transfers

```python
from decimal import Decimal

# To a blockchain address
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
    amount=Decimal("10.00"),
    purpose="Server hosting payment"
)

if result.success:
    print(f"Sent! TX: {result.blockchain_tx}")
else:
    print(f"Failed: {result.error}")
```

### x402 API Payments

Pay for API access using the HTTP 402 protocol:

```python
# Pay for API access
result = await client.pay(
    wallet_id=wallet.id,
    recipient="https://api.premium-data.com/v1/resource",
    amount=Decimal("0.10")  # Or let x402 negotiate price
)

# The SDK:
# 1. Makes GET request to URL
# 2. Receives 402 with price in headers
# 3. Pays the invoice
# 4. Retries with payment proof
# 5. Returns the API response
```

### Cross-Chain Transfers

Move USDC between blockchains using Circle's CCTP:

```python
from paykit import Network

# Transfer from Arc to Base
result = await client.pay(
    wallet_id=arc_wallet.id,
    recipient="0xRecipientOnBase...",
    amount=Decimal("100.00"),
    destination_chain=Network.BASE
)

# Fast transfer (2-5 seconds) - agent-side minting
# Standard transfer (13-19 minutes) - automatic attestation
```

### Simulating Payments

Test without spending:

```python
simulation = await client.simulate(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("1000.00")
)

if simulation.would_succeed:
    print(f"Would use: {simulation.payment_method}")
    print(f"Estimated fee: {simulation.estimated_fee}")
else:
    print(f"Would fail: {simulation.reason}")
```

### Batch Payments

Execute multiple payments concurrently:

```python
from paykit import PaymentRequest

requests = [
    PaymentRequest(wallet_id=w.id, recipient="0xA...", amount=Decimal("10.00")),
    PaymentRequest(wallet_id=w.id, recipient="0xB...", amount=Decimal("20.00")),
    PaymentRequest(wallet_id=w.id, recipient="0xC...", amount=Decimal("30.00")),
]

results = await client.batch_pay(requests, concurrency=5)

print(f"Success: {results.success_count}")
print(f"Failed: {results.failed_count}")
print(f"Total sent: {results.total_amount}")

# Check individual results
for r in results.results:
    if not r.success:
        print(f"Failed: {r.recipient} - {r.error}")
```

---

## Safety Guards

### The Safety Kernel

Guards are checked atomically before every payment. If any guard fails, the payment is rejected.

```python
# Recommended: Always add guards before funding a wallet
await client.add_budget_guard(wallet.id, daily_limit=Decimal("100.00"))
await client.add_rate_limit_guard(wallet.id, max_per_hour=10)
await client.add_single_tx_guard(wallet.id, max_amount=Decimal("25.00"))
```

### Budget Guards

```python
# Daily spending limit
await client.add_budget_guard(
    wallet.id,
    daily_limit=Decimal("100.00"),
    name="daily_budget"
)

# Multi-tier limits
await client.add_budget_guard(
    wallet.id,
    hourly_limit=Decimal("25.00"),
    daily_limit=Decimal("100.00"),
    total_limit=Decimal("1000.00"),
    name="tiered_budget"
)
```

### Rate Limit Guards

Prevent runaway loops:

```python
await client.add_rate_limit_guard(
    wallet.id,
    max_per_minute=5,    # Prevent infinite loops
    max_per_hour=20,     # Reasonable hourly limit
    max_per_day=100,     # Daily cap
    name="rate_limits"
)
```

### Recipient Guards

Control who can receive payments:

```python
# Whitelist mode - only allow specific recipients
await client.add_recipient_guard(
    wallet.id,
    mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com"],
    addresses=["0xTrustedVendor..."],
    name="approved_recipients"
)

# Blacklist mode - block specific recipients
await client.add_recipient_guard(
    wallet.id,
    mode="blacklist",
    addresses=["0xScamAddress..."],
    patterns=[r".*\.suspicious\.com"],
    name="blocked_recipients"
)
```

### Confirmation Guards

Human-in-the-loop for large payments:

```python
# Require confirmation for payments over $500
await client.add_confirm_guard(
    wallet.id,
    threshold=Decimal("500.00"),
    name="large_payment_approval"
)

# With callback
async def approval_callback(context):
    # Send notification, wait for approval
    approved = await notify_and_wait(context)
    return approved

await client.add_confirm_guard(
    wallet.id,
    threshold=Decimal("100.00"),
    callback=approval_callback,
    name="approval_flow"
)
```

### Guard Management

```python
# List guards
guards = await client.list_guards(wallet.id)
for g in guards:
    print(f"{g.name}: {g.guard_type}")

# Remove a guard
await client.remove_guard(wallet.id, "old_budget")
```

---

## Multi-Agent Patterns

### Payment Intents for Coordination

Agent A proposes, Agent B approves:

```python
# Agent A: Create intent
intent = await client.create_payment_intent(
    wallet_id=wallet.id,
    recipient="0xSupplier...",
    amount=Decimal("500.00"),
    purpose="Q1 supply order",
    metadata={"order_id": "ORD-123"}
)
print(f"Intent created: {intent.id}")
# Budget is reserved but not spent

# Agent B: Review and confirm
intent = await client.get_payment_intent(intent.id)
if intent.status == "requires_confirmation":
    # Verify the intent is valid
    if approve_order(intent.metadata["order_id"]):
        result = await client.confirm_payment_intent(intent.id)
    else:
        await client.cancel_payment_intent(intent.id)
```

### Shared Wallet Sets

Multiple agents sharing a budget:

```python
# Create shared wallet set with guards
swarm_set = await client.create_wallet_set(name="marketing-swarm")

# Apply guards to the wallet set (affects all wallets)
await client.add_budget_guard(
    wallet_set_id=swarm_set.id,
    daily_limit=Decimal("500.00"),
    name="swarm_budget"
)

# Create wallets for each agent
for agent_name in ["seo-agent", "ads-agent", "content-agent"]:
    wallet = await client.create_wallet(
        wallet_set_id=swarm_set.id,
        name=agent_name
    )
```

---

## Integration Examples

### LangChain Integration

```python
from langchain.tools import Tool
from paykit import PayKit
from decimal import Decimal

client = PayKit()

async def pay_tool(recipient: str, amount: str, purpose: str) -> str:
    """Pay a recipient in USDC."""
    result = await client.pay(
        wallet_id=AGENT_WALLET_ID,
        recipient=recipient,
        amount=Decimal(amount),
        purpose=purpose
    )
    if result.success:
        return f"Payment successful. TX: {result.blockchain_tx}"
    return f"Payment failed: {result.error}"

payment_tool = Tool(
    name="pay",
    description="Pay a recipient in USDC. Input: recipient address, amount, purpose",
    func=pay_tool
)
```

### Google Gemini Integration

```python
import google.generativeai as genai
from paykit import PayKit
from decimal import Decimal

client = PayKit()

# Define payment function for Gemini
pay_function = {
    "name": "make_payment",
    "description": "Send USDC payment to an address",
    "parameters": {
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Recipient address"},
            "amount": {"type": "number", "description": "Amount in USDC"},
            "purpose": {"type": "string", "description": "Payment purpose"}
        },
        "required": ["recipient", "amount"]
    }
}

async def handle_payment_call(function_call):
    args = function_call.args
    result = await client.pay(
        wallet_id=WALLET_ID,
        recipient=args["recipient"],
        amount=Decimal(str(args["amount"])),
        purpose=args.get("purpose")
    )
    return {"success": result.success, "tx": result.blockchain_tx}
```

### FastAPI Webhook Handler

```python
from fastapi import FastAPI, Request, HTTPException
from paykit import PayKit

app = FastAPI()
client = PayKit()

@app.post("/webhooks/circle")
async def handle_webhook(request: Request):
    body = await request.body()
    headers = dict(request.headers)
    
    try:
        event = client.webhooks.handle(body, headers)
        
        if event.notification_type == "transactions":
            # Handle transaction update
            tx_id = event.data.get("id")
            status = event.data.get("state")
            print(f"Transaction {tx_id}: {status}")
        
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, str(e))
```

---

## Production Deployment

### Environment Configuration

```bash
# Production settings
CIRCLE_API_KEY=prod-api-key
ENTITY_SECRET=prod-entity-secret
PAYKIT_NETWORK=BASE  # Use mainnet
PAYKIT_STORAGE_BACKEND=redis
PAYKIT_REDIS_URL=redis://prod-redis:6379/0
PAYKIT_LOG_LEVEL=WARNING
```

### Redis for Production

```python
# Redis storage is required for:
# - Guard atomicity across multiple instances
# - Persistent transaction history
# - Rate limiting accuracy

# Set environment variable
export PAYKIT_STORAGE_BACKEND=redis
export PAYKIT_REDIS_URL=redis://localhost:6379/0
```

### Error Handling

```python
from paykit import (
    PayKitError,
    GuardError,
    InsufficientBalanceError,
    NetworkError,
)

async def safe_payment(wallet_id, recipient, amount):
    try:
        result = await client.pay(
            wallet_id=wallet_id,
            recipient=recipient,
            amount=amount
        )
        return {"success": True, "tx": result.blockchain_tx}
    
    except GuardError as e:
        # Don't retry - guard will keep blocking
        logger.warning(f"Guard blocked payment: {e}")
        return {"success": False, "error": "Payment blocked by policy"}
    
    except InsufficientBalanceError as e:
        # Don't retry - need to add funds
        logger.error(f"Insufficient balance: {e}")
        return {"success": False, "error": "Insufficient funds"}
    
    except NetworkError as e:
        # Can retry
        logger.warning(f"Network error: {e}")
        raise  # Let retry logic handle it
    
    except PayKitError as e:
        logger.error(f"Payment failed: {e}")
        return {"success": False, "error": str(e)}
```

### Logging

```python
import logging
from paykit import PayKit

# Configure logging
logging.basicConfig(level=logging.INFO)

# Or use PayKit's logger
client = PayKit(log_level=logging.DEBUG)

# Log levels:
# DEBUG - Full request/response tracing
# INFO - Payment lifecycle events
# WARNING - Recoverable issues
# ERROR - Failures
```

---

## Troubleshooting

### Entity Secret Issues

**Error:** "Entity secret invalid"

```python
# The entity secret registered with Circle doesn't match your .env

# Solution 1: If you have a recovery file
# Go to console.circle.com > Developer > Entity Secret
# Upload recovery file from ~/.config/paykit/

# Solution 2: Create new API key
# 1. Create new key at console.circle.com
# 2. Delete ENTITY_SECRET from .env
# 3. Restart app (will auto-generate new secret)
```

### Guard Blocking Payments

```python
# Check which guard is blocking
try:
    await client.pay(...)
except GuardError as e:
    print(f"Blocked by: {e.details.get('guard_name')}")
    print(f"Reason: {e.message}")

# List current guards
guards = await client.list_guards(wallet.id)
for g in guards:
    print(f"{g.name}: {g.config}")
```

### Transaction Pending

```python
# Check transaction status
from paykit import PaymentStatus

result = await client.pay(...)
if result.status == PaymentStatus.PENDING:
    # Wait for confirmation
    await asyncio.sleep(5)
    updated = await client.sync_transaction(result.transaction_id)
    print(f"Updated status: {updated.status}")
```

### Cross-Chain Transfer Slow

```python
# CCTP has two modes:
# - Fast (2-5s): Requires agent to call receiveMessage
# - Standard (13-19min): Automatic attestation

# For fast transfers, ensure wallet has gas on destination chain
# Check gas requirements in docs/GAS_REQUIREMENTS.md
```

### Connection Errors

```python
from paykit import NetworkError

try:
    await client.pay(...)
except NetworkError as e:
    if "timeout" in str(e).lower():
        # Increase timeout
        client = PayKit()
        client.config = client.config.with_updates(request_timeout=60.0)
    elif "rate limit" in str(e).lower():
        # Back off and retry
        await asyncio.sleep(5)
```
