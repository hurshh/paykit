# PayKit

[![PyPI version](https://img.shields.io/pypi/v/paykit.svg)](https://pypi.org/project/paykit/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-236%20passed-brightgreen.svg)]()
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Vendor-Agnostic Payment SDK for Autonomous AI Agents**

PayKit provides a unified payment infrastructure for AI agents. One SDK to handle wallets, transfers, spending controls, and cross-chain payments across multiple providers.

## Why PayKit?

| Challenge | Solution |
|-----------|----------|
| AI agents need to spend money | Programmatic USDC wallets with no private keys to manage |
| Agents can hallucinate or overspend | Safety guards with atomic enforcement |
| Different payment protocols exist | Universal routing (direct, x402, cross-chain) |
| Vendor lock-in | Provider abstraction (Circle, Coinbase, more) |
| No visibility into agent spending | Built-in ledger and transaction history |

## Installation

```bash
pip install paykit
```

With Coinbase support:
```bash
pip install paykit[coinbase]
```

## Quick Start

```python
import asyncio
from decimal import Decimal
from paykit import PayKit

async def main():
    # Initialize (reads CIRCLE_API_KEY from environment)
    client = PayKit()
    
    # Create a wallet for your agent
    wallet_set, wallet = await client.create_agent_wallet(agent_name="my-agent")
    print(f"Wallet: {wallet.address}")
    
    # Add spending limits (safety first!)
    await client.add_budget_guard(wallet.id, daily_limit=Decimal("100.00"))
    
    # Make a payment
    result = await client.pay(
        wallet_id=wallet.id,
        recipient="RECEPIENT_WALLET_ID",
        amount=Decimal("10.00")
    )
    print(f"Payment: {result.status}")

asyncio.run(main())
```

## Core Features

### Wallet Management

Create and manage USDC wallets programmatically. No seed phrases or private keys.

```python
# Create wallets for agents
wallet_set, wallet = await client.create_agent_wallet(agent_name="trading-bot")

# Check balance
balance = await client.get_balance(wallet.id)

# List all wallets
wallets = client.wallet.list_wallets()
```

### Safety Guards

Protect against runaway spending with atomic enforcement:

```python
# Budget limits
await client.add_budget_guard(
    wallet.id,
    daily_limit=Decimal("100.00"),
    hourly_limit=Decimal("25.00"),
    total_limit=Decimal("1000.00")
)

# Rate limits (prevent infinite loops)
await client.add_rate_limit_guard(wallet.id, max_per_minute=5, max_per_hour=20)

# Transaction size limits
await client.add_single_tx_guard(wallet.id, max_amount=Decimal("50.00"))

# Recipient whitelist
await client.add_recipient_guard(
    wallet.id,
    mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com"]
)

# Human approval for large payments
await client.add_confirm_guard(wallet.id, threshold=Decimal("500.00"))
```

| Guard | Purpose |
|-------|---------|
| `BudgetGuard` | Spending limits (daily/hourly/total) |
| `RateLimitGuard` | Transaction frequency limits |
| `SingleTxGuard` | Per-transaction min/max amounts |
| `RecipientGuard` | Whitelist or blacklist recipients |
| `ConfirmGuard` | Human-in-the-loop approval |

### Universal Payment Routing

One `pay()` method handles all payment types:

```python
# Direct USDC transfer (blockchain address)
await client.pay(wallet_id=w, recipient="0x...", amount=Decimal("10.00"))

# x402 API payment (HTTP URL)
await client.pay(wallet_id=w, recipient="https://api.example.com/data", amount=Decimal("0.10"))

# Cross-chain transfer (CCTP)
from paykit import Network
await client.pay(
    wallet_id=w,
    recipient="0x...",
    amount=Decimal("50.00"),
    destination_chain=Network.BASE
)
```

### Payment Intents

Authorize now, execute later:

```python
# Create authorization
intent = await client.create_payment_intent(
    wallet_id=wallet.id,
    recipient="0x...",
    amount=Decimal("500.00")
)

# Confirm when ready
result = await client.confirm_payment_intent(intent.id)

# Or cancel
await client.cancel_payment_intent(intent.id)
```

### Batch Payments

Execute multiple payments concurrently:

```python
from paykit import PaymentRequest

results = await client.batch_pay([
    PaymentRequest(wallet_id=w, recipient="0xA...", amount=Decimal("10.00")),
    PaymentRequest(wallet_id=w, recipient="0xB...", amount=Decimal("20.00")),
    PaymentRequest(wallet_id=w, recipient="0xC...", amount=Decimal("30.00")),
], concurrency=10)

print(f"Success: {results.success_count}, Failed: {results.failed_count}")
```

### Transaction Ledger

Complete observability:

```python
# Get transaction history
history = await client.ledger.get_history(wallet_id=wallet.id)

# Get total spent
total = await client.ledger.get_total_spent(wallet_id=wallet.id)

# Sync with blockchain
await client.sync_transaction(entry_id="...")
```

## Multi-Provider Architecture

PayKit abstracts wallet providers. Switch providers without code changes.

### Supported Providers

| Provider | Status | Install | Features |
|----------|--------|---------|----------|
| [Circle](https://circle.com) | Stable | Default | CCTP, gasless transfers |
| [Coinbase](https://coinbase.com) | Beta | `pip install paykit[coinbase]` | EVM + Solana |

### Provider Configuration

**Circle (Default):**
```python
from paykit import PayKit
from paykit.providers import CircleProvider, CircleConfig

provider = CircleProvider(CircleConfig(
    api_key="your-circle-api-key",
    entity_secret="your-entity-secret",  # Auto-generated if not provided
))
client = PayKit(provider=provider)
```

**Coinbase:**
```python
from paykit.providers import CoinbaseProvider, CoinbaseConfig

provider = CoinbaseProvider(CoinbaseConfig(
    api_key="your-cdp-api-key-id",
    api_secret="your-cdp-api-key-secret",
    wallet_secret="your-wallet-secret",
))
client = PayKit(provider=provider)
```

**Environment Variables:**
```bash
# Circle
export CIRCLE_API_KEY="..."
export ENTITY_SECRET="..."  # Optional, auto-generated

# Coinbase
export CDP_API_KEY_ID="..."
export CDP_API_KEY_SECRET="..."
export CDP_WALLET_SECRET="..."

# Provider selection
export PAYKIT_PROVIDER="circle"  # or "coinbase"
```

### Direct Provider Access

```python
from paykit.providers import get_provider, ProviderType

# Get provider
provider = get_provider(ProviderType.CIRCLE)

# Direct operations
wallet = await provider.create_wallet(wallet_set_id, "ETH-SEPOLIA")
balances = await provider.get_balances(wallet.id)
result = await provider.transfer(wallet.id, "0x...", Decimal("10.00"))
```

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `CIRCLE_API_KEY` | Yes* | Circle API key | - |
| `ENTITY_SECRET` | No | Circle entity secret | Auto-generated |
| `PAYKIT_PROVIDER` | No | Provider: `circle`, `coinbase` | `circle` |
| `PAYKIT_NETWORK` | No | Default network | `ARC-TESTNET` |
| `PAYKIT_STORAGE_BACKEND` | No | Storage: `memory`, `redis` | `memory` |
| `PAYKIT_REDIS_URL` | No | Redis connection URL | `redis://localhost:6379` |
| `PAYKIT_LOG_LEVEL` | No | Logging level | `INFO` |

### Supported Networks

**Testnets:**
- `ARC-TESTNET` (Circle Arc - recommended for testing)
- `ETH-SEPOLIA`, `BASE-SEPOLIA`, `ARB-SEPOLIA`
- `MATIC-AMOY`, `AVAX-FUJI`
- `SOL-DEVNET`

**Mainnets:**
- `ETH`, `BASE`, `ARB`, `MATIC`, `AVAX`, `SOL`

## Error Handling

```python
from paykit import (
    PayKitError,      # Base exception
    GuardError,         # Blocked by safety guard
    InsufficientBalanceError,
    WalletError,
    PaymentError,
    ConfigurationError,
)

try:
    result = await client.pay(wallet_id=w, recipient="0x...", amount=Decimal("1000.00"))
except GuardError as e:
    print(f"Blocked: {e}")  # Budget exceeded, rate limited, etc.
except InsufficientBalanceError as e:
    print(f"Low balance: {e}")
except PayKitError as e:
    print(f"Payment failed: {e}")
```

## Examples

See the [examples/](examples/) directory:

- [`basic_payment.py`](examples/basic_payment.py) - Simple payment flow
- [`using_guards.py`](examples/using_guards.py) - Safety guard configuration
- [`gemini_agent.py`](examples/gemini_agent.py) - Google Gemini integration
- [`x402_client_demo.py`](examples/x402_client_demo.py) - x402 protocol usage
- [`ledger_tracking.py`](examples/ledger_tracking.py) - Transaction observability

## Documentation

| Document | Description |
|----------|-------------|
| [Quickstart](docs/QUICKSTART.md) | Get started in 5 minutes |
| [API Reference](docs/API_REFERENCE.md) | Complete API documentation |
| [SDK Usage Guide](docs/SDK_USAGE_GUIDE.md) | Detailed usage patterns |
| [CCTP Usage](docs/CCTP_USAGE.md) | Cross-chain transfer guide |
| [Gas Requirements](docs/GAS_REQUIREMENTS.md) | Network gas information |
| [Architecture](docs/PAYKIT_VISION.md) | Design philosophy |

## Development

```bash
# Clone repository
git clone https://github.com/paykit/paykit.git
cd paykit

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/paykit

# Type checking
mypy src/paykit

# Linting
ruff check src/paykit
ruff format src/paykit
```

### Project Structure

```
src/paykit/
├── client.py           # Main PayKit client
├── providers/          # Wallet provider implementations
│   ├── base.py         # Abstract provider interface
│   ├── circle.py       # Circle implementation
│   └── coinbase.py     # Coinbase implementation
├── guards/             # Safety guard system
├── protocols/          # Payment protocol adapters
├── ledger/             # Transaction history
├── storage/            # Persistence backends
└── webhooks/           # Event handling
```

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [PyPI Package](https://pypi.org/project/paykit/)
- [GitHub Repository](https://github.com/paykit/paykit)
- [Documentation](https://paykit.dev/docs)
- [Circle Developer Docs](https://developers.circle.com)
- [Coinbase CDP Docs](https://docs.cdp.coinbase.com)
