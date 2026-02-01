# PayKit API Reference

Complete API documentation for the PayKit SDK.

## Table of Contents

- [PayKit Client](#paykit-client)
- [Wallet Operations](#wallet-operations)
- [Payment Operations](#payment-operations)
- [Safety Guards](#safety-guards)
- [Payment Intents](#payment-intents)
- [Ledger](#ledger)
- [Providers](#providers)
- [Types](#types)
- [Exceptions](#exceptions)

---

## PayKit Client

The main entry point for the SDK.

### Constructor

```python
from paykit import PayKit, Network

client = PayKit(
    circle_api_key: str | None = None,      # Circle API key (or from env)
    entity_secret: str | None = None,        # Entity secret (auto-generated if missing)
    network: Network = Network.ARC_TESTNET,  # Target blockchain network
    log_level: int | str | None = None,      # Logging level
    provider: WalletProvider | None = None,  # Custom wallet provider
)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `config` | `Config` | SDK configuration |
| `wallet` | `WalletService` | Wallet management service |
| `guards` | `GuardManager` | Guard management |
| `ledger` | `Ledger` | Transaction ledger |
| `webhooks` | `WebhookParser` | Webhook handling |
| `provider` | `WalletProvider | None` | Custom provider (if set) |

### Context Manager

```python
async with PayKit() as client:
    result = await client.pay(...)
```

---

## Wallet Operations

### create_agent_wallet

Create a wallet for an AI agent.

```python
wallet_set, wallet = await client.create_agent_wallet(
    agent_name: str,                    # Agent identifier
    blockchain: Network | None = None,  # Target blockchain
)
```

**Returns:** `tuple[WalletSetInfo, WalletInfo]`

### create_user_wallet

Create a wallet for an end user.

```python
wallet_set, wallet = await client.create_user_wallet(
    user_id: str,                       # User identifier
    blockchain: Network | None = None,  # Target blockchain
)
```

**Returns:** `tuple[WalletSetInfo, WalletInfo]`

### create_wallet

Create a wallet in an existing wallet set.

```python
wallet = await client.create_wallet(
    blockchain: Network | str | None = None,  # Target blockchain
    wallet_set_id: str | None = None,         # Existing wallet set ID
    account_type: AccountType = AccountType.EOA,
    name: str | None = None,                  # Wallet set name (if creating new)
)
```

**Returns:** `WalletInfo`

### create_wallet_set

Create a new wallet set.

```python
wallet_set = await client.create_wallet_set(
    name: str | None = None,  # Wallet set name
)
```

**Returns:** `WalletSetInfo`

### get_balance

Get USDC balance for a wallet.

```python
balance = await client.get_balance(wallet_id: str)
```

**Returns:** `Decimal`

### list_wallets

List all wallets.

```python
wallets = client.wallet.list_wallets(
    wallet_set_id: str | None = None,  # Filter by wallet set
)
```

**Returns:** `list[WalletInfo]`

---

## Payment Operations

### pay

Execute a payment. Automatically routes to the correct protocol.

```python
result = await client.pay(
    wallet_id: str,                          # Source wallet
    recipient: str,                          # Address, URL, or domain
    amount: Decimal | str | float,           # Amount in USDC
    destination_chain: Network | None = None,  # For cross-chain
    purpose: str | None = None,              # Description for ledger
    metadata: dict | None = None,            # Custom metadata
    idempotency_key: str | None = None,      # Prevent duplicates
    fee_level: FeeLevel = FeeLevel.MEDIUM,   # Gas fee level
    wait_for_completion: bool = False,       # Block until confirmed
    timeout_seconds: float = 30.0,           # Timeout for waiting
    skip_guards: bool = False,               # Bypass safety guards (dangerous)
)
```

**Returns:** `PaymentResult`

**Routing Logic:**
- `0x...` or Solana address → `TransferAdapter` (direct transfer)
- `https://...` → `X402Adapter` (HTTP 402 payment)
- `destination_chain` specified → `GatewayAdapter` (CCTP cross-chain)

### simulate

Simulate a payment without executing.

```python
simulation = await client.simulate(
    wallet_id: str,
    recipient: str,
    amount: Decimal | str | float,
    destination_chain: Network | None = None,
)
```

**Returns:** `SimulationResult`

```python
@dataclass
class SimulationResult:
    would_succeed: bool
    payment_method: PaymentMethod
    estimated_fee: Decimal | None
    reason: str | None  # If would_succeed is False
```

### batch_pay

Execute multiple payments concurrently.

```python
from paykit import PaymentRequest

results = await client.batch_pay(
    requests: list[PaymentRequest],
    concurrency: int = 5,  # Max concurrent payments
)
```

**Returns:** `BatchPaymentResult`

```python
@dataclass
class BatchPaymentResult:
    results: list[PaymentResult]
    success_count: int
    failed_count: int
    total_amount: Decimal
```

---

## Safety Guards

Guards are checked atomically before every payment.

### add_budget_guard

Enforce spending limits.

```python
await client.add_budget_guard(
    wallet_id: str,
    daily_limit: Decimal | str | None = None,   # Max per 24 hours
    hourly_limit: Decimal | str | None = None,  # Max per hour
    total_limit: Decimal | str | None = None,   # Lifetime max
    name: str = "budget",                       # Guard identifier
)
```

### add_rate_limit_guard

Limit transaction frequency.

```python
await client.add_rate_limit_guard(
    wallet_id: str,
    max_per_minute: int | None = None,
    max_per_hour: int | None = None,
    max_per_day: int | None = None,
    name: str = "rate_limit",
)
```

### add_single_tx_guard

Limit individual transaction amounts.

```python
await client.add_single_tx_guard(
    wallet_id: str,
    max_amount: Decimal | str | None = None,
    min_amount: Decimal | str | None = None,
    name: str = "single_tx",
)
```

### add_recipient_guard

Control allowed recipients.

```python
await client.add_recipient_guard(
    wallet_id: str,
    mode: str = "whitelist",  # "whitelist" or "blacklist"
    addresses: list[str] | None = None,  # Blockchain addresses
    domains: list[str] | None = None,    # Domain names
    patterns: list[str] | None = None,   # Regex patterns
    name: str = "recipient",
)
```

### add_confirm_guard

Require confirmation for large payments.

```python
await client.add_confirm_guard(
    wallet_id: str,
    threshold: Decimal | str,              # Amount requiring confirmation
    require_all: bool = False,             # Require for all payments
    callback: Callable | None = None,      # Confirmation callback
    name: str = "confirm",
)
```

### list_guards

List guards for a wallet.

```python
guards = await client.list_guards(wallet_id: str)
```

**Returns:** `list[GuardConfig]`

### remove_guard

Remove a guard.

```python
await client.remove_guard(wallet_id: str, guard_name: str)
```

---

## Payment Intents

Authorize payments for later execution.

### create_payment_intent

Create a payment authorization.

```python
intent = await client.create_payment_intent(
    wallet_id: str,
    recipient: str,
    amount: Decimal | str | float,
    purpose: str | None = None,
    metadata: dict | None = None,
    expires_in_seconds: int = 3600,  # 1 hour default
)
```

**Returns:** `PaymentIntent`

### confirm_payment_intent

Execute a payment intent.

```python
result = await client.confirm_payment_intent(intent_id: str)
```

**Returns:** `PaymentResult`

### cancel_payment_intent

Cancel a payment intent (releases reserved budget).

```python
await client.cancel_payment_intent(intent_id: str)
```

### get_payment_intent

Get intent status.

```python
intent = await client.get_payment_intent(intent_id: str)
```

**Returns:** `PaymentIntent`

---

## Ledger

Transaction history and observability.

### get_history

Get transaction history.

```python
entries = await client.ledger.get_history(
    wallet_id: str,
    limit: int = 100,
    offset: int = 0,
)
```

**Returns:** `list[LedgerEntry]`

### get_total_spent

Get total amount spent.

```python
total = await client.ledger.get_total_spent(wallet_id: str)
```

**Returns:** `Decimal`

### record

Record a transaction (internal use).

```python
await client.ledger.record(entry: LedgerEntry)
```

---

## Providers

### WalletProvider Interface

Abstract base class for wallet providers.

```python
from paykit.providers import WalletProvider

class WalletProvider(ABC):
    @property
    def provider_type(self) -> ProviderType: ...
    @property
    def supported_blockchains(self) -> list[str]: ...
    
    async def list_wallet_sets(self) -> list[WalletSetInfo]: ...
    async def create_wallet_set(self, name: str) -> WalletSetInfo: ...
    async def get_wallet_set(self, wallet_set_id: str) -> WalletSetInfo | None: ...
    
    async def list_wallets(self, wallet_set_id: str | None = None) -> list[WalletInfo]: ...
    async def create_wallet(self, wallet_set_id: str, blockchain: str, name: str | None = None) -> WalletInfo: ...
    async def get_wallet(self, wallet_id: str) -> WalletInfo | None: ...
    
    async def get_balances(self, wallet_id: str) -> list[TokenBalance]: ...
    async def get_usdc_balance(self, wallet_id: str) -> Decimal: ...
    
    async def transfer(self, wallet_id: str, recipient: str, amount: Decimal, token_symbol: str = "USDC") -> TransactionResult: ...
    async def get_transaction(self, transaction_id: str) -> TransactionResult | None: ...
    
    async def execute_contract(self, wallet_id: str, contract_address: str, abi: list, function_name: str, params: list) -> ContractCallResult: ...
```

### get_provider

Factory function to get a provider instance.

```python
from paykit.providers import get_provider, ProviderType

provider = get_provider(
    provider_type: ProviderType | str | None = None,  # Provider type
    **kwargs,  # Provider-specific config
)
```

### CircleProvider

Circle Developer-Controlled Wallets.

```python
from paykit.providers import CircleProvider, CircleConfig

config = CircleConfig(
    api_key: str,
    entity_secret: str = "",
    environment: str = "testnet",
)
provider = CircleProvider(config)
```

### CoinbaseProvider

Coinbase Developer Platform.

```python
from paykit.providers import CoinbaseProvider, CoinbaseConfig

config = CoinbaseConfig(
    api_key: str,       # CDP_API_KEY_ID
    api_secret: str,    # CDP_API_KEY_SECRET
    wallet_secret: str, # CDP_WALLET_SECRET
)
provider = CoinbaseProvider(config)
```

---

## Types

### Network

Supported blockchain networks.

```python
from paykit import Network

class Network(str, Enum):
    # Testnets
    ARC_TESTNET = "ARC-TESTNET"
    ETH_SEPOLIA = "ETH-SEPOLIA"
    BASE_SEPOLIA = "BASE-SEPOLIA"
    ARB_SEPOLIA = "ARB-SEPOLIA"
    MATIC_AMOY = "MATIC-AMOY"
    AVAX_FUJI = "AVAX-FUJI"
    SOL_DEVNET = "SOL-DEVNET"
    
    # Mainnets
    ETH = "ETH"
    BASE = "BASE"
    ARB = "ARB"
    MATIC = "MATIC"
    AVAX = "AVAX"
    SOL = "SOL"
```

### PaymentResult

Result of a payment operation.

```python
@dataclass
class PaymentResult:
    success: bool
    transaction_id: str | None
    status: PaymentStatus
    amount: Decimal
    recipient: str
    blockchain_tx: str | None
    fee: Decimal | None
    error: str | None
    metadata: dict
```

### PaymentStatus

```python
class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### WalletInfo

```python
@dataclass
class WalletInfo:
    id: str
    address: str
    blockchain: str
    name: str | None
    state: str
    wallet_set_id: str | None
```

### WalletSetInfo

```python
@dataclass
class WalletSetInfo:
    id: str
    name: str
    custody_type: str
```

---

## Exceptions

All exceptions inherit from `PayKitError`.

```python
from paykit import (
    PayKitError,           # Base exception
    ConfigurationError,      # Invalid configuration
    WalletError,             # Wallet operations failed
    PaymentError,            # Payment failed
    GuardError,              # Blocked by safety guard
    ProtocolError,           # Protocol adapter error
    ValidationError,         # Invalid input
    InsufficientBalanceError,  # Not enough funds
    NetworkError,            # Network/API error
    X402Error,               # x402 protocol error
    CrosschainError,         # CCTP error
    TransactionTimeoutError, # Transaction timed out
    IdempotencyError,        # Duplicate request
)
```

### Exception Hierarchy

```
PayKitError
├── ConfigurationError
├── WalletError
├── PaymentError
│   ├── InsufficientBalanceError
│   ├── GuardError
│   └── TransactionTimeoutError
├── ProtocolError
│   ├── X402Error
│   └── CrosschainError
├── ValidationError
├── NetworkError
└── IdempotencyError
```

---

## Webhooks

Parse and verify Circle webhook events.

```python
from paykit import PayKit

client = PayKit()

# In your webhook handler
event = client.webhooks.handle(
    payload: bytes,          # Raw request body
    headers: dict[str, str], # Request headers
)

if event.notification_type == "transactions":
    print(f"Transaction update: {event.data}")
```

### WebhookEvent

```python
@dataclass
class WebhookEvent:
    notification_type: NotificationType
    data: dict
    timestamp: datetime
    signature_valid: bool
```

---

## Storage Backends

Configurable persistence for guards and ledger.

```python
# Environment variable
export PAYKIT_STORAGE_BACKEND="redis"
export PAYKIT_REDIS_URL="redis://localhost:6379/0"
```

### InMemoryStorage

Default for development. Data is lost on restart.

### RedisStorage

Production-ready with distributed locking.

```python
from paykit.storage import RedisStorage

storage = RedisStorage(redis_url="redis://localhost:6379/0")
```
