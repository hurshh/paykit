"""
PayKit - Payment SDK for Autonomous AI Agents

Vendor-agnostic payment infrastructure supporting Circle, Coinbase, and more.

Quick Start:
    >>> from paykit import PayKit
    >>> 
    >>> client = PayKit()  # Uses Circle by default
    >>> result = await client.pay(wallet_id="...", recipient="0x...", amount=10.00)

With Custom Provider:
    >>> from paykit import PayKit
    >>> from paykit.providers import CircleProvider, CircleConfig
    >>> 
    >>> provider = CircleProvider(CircleConfig(api_key="...", entity_secret="..."))
    >>> client = PayKit(provider=provider)
"""

from paykit.client import PayKit
from paykit.core.config import Config
from paykit.core.exceptions import (
    ConfigurationError,
    GuardError,
    InsufficientBalanceError,
    NetworkError,
    PayKitError,
    PaymentError,
    ProtocolError,
    WalletError,
    X402Error,
)
from paykit.core.types import (
    Balance,
    FeeLevel,
    Network,
    PaymentMethod,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
    SimulationResult,
    TokenInfo,
    TransactionInfo,
    WalletInfo,
    WalletSetInfo,
)

# Import guards for convenience
from paykit.guards import (
    BudgetGuard,
    ConfirmGuard,
    Guard,
    GuardChain,
    GuardResult,
    PaymentContext,
    RateLimitGuard,
    RecipientGuard,
    SingleTxGuard,
)
from paykit.onboarding import (
    ensure_setup,
    find_recovery_file,
    generate_entity_secret,
    get_config_dir,
    print_setup_status,
    quick_setup,
    verify_setup,
)

__version__ = "0.0.1"
__all__ = [
    # Main Client
    "PayKit",
    # Setup utilities
    "quick_setup",
    "ensure_setup",
    "generate_entity_secret",
    "verify_setup",

    "print_setup_status",
    "find_recovery_file",
    "get_config_dir",
    # Types
    "Network",
    "FeeLevel",
    "PaymentMethod",
    "PaymentStatus",
    "WalletInfo",
    "WalletSetInfo",
    "Balance",
    "TokenInfo",
    "PaymentRequest",
    "PaymentResult",
    "SimulationResult",
    "TransactionInfo",
    # Config
    "Config",
    # Exceptions
    "PayKitError",
    "ConfigurationError",
    "WalletError",
    "PaymentError",
    "GuardError",
    "ProtocolError",
    "InsufficientBalanceError",
    "NetworkError",
    "X402Error",
    # Guards
    "Guard",
    "GuardChain",
    "GuardResult",
    "PaymentContext",
    "BudgetGuard",
    "SingleTxGuard",
    "RecipientGuard",
    "RateLimitGuard",
    "ConfirmGuard",
]
