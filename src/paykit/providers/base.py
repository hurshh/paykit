"""
Abstract wallet provider interface.

This module defines the contract that all wallet providers must implement,
enabling PayKit to work with Circle, Coinbase, or any other wallet infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class ProviderType(str, Enum):
    """Supported wallet provider types."""
    CIRCLE = "circle"
    COINBASE = "coinbase"
    # Future providers can be added here


class TransactionState(str, Enum):
    """Universal transaction states across providers."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProviderConfig:
    """Base configuration for wallet providers."""
    api_key: str
    environment: str = "testnet"  # "testnet" or "mainnet"
    timeout: float = 30.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class WalletInfo:
    """Universal wallet representation across providers."""
    id: str
    address: str
    blockchain: str
    name: str | None = None
    state: str = "LIVE"
    provider: ProviderType = ProviderType.CIRCLE
    # Provider-specific data
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class WalletSetInfo:
    """Universal wallet set/group representation."""
    id: str
    name: str
    custody_type: str = "DEVELOPER"
    provider: ProviderType = ProviderType.CIRCLE
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass 
class TokenBalance:
    """Universal token balance representation."""
    token_id: str
    token_symbol: str
    amount: Decimal
    blockchain: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionResult:
    """Universal transaction result across providers."""
    id: str
    state: TransactionState
    tx_hash: str | None = None
    amount: Decimal | None = None
    fee: Decimal | None = None
    error_message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractCallResult:
    """Result of a smart contract call."""
    id: str
    state: TransactionState
    tx_hash: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class WalletProvider(ABC):
    """
    Abstract base class for wallet providers.
    
    All wallet infrastructure providers (Circle, Coinbase, etc.) must implement
    this interface to work with PayKit.
    
    Example:
        >>> provider = CircleProvider(config)
        >>> wallet = await provider.create_wallet("my-wallet", "ETH-SEPOLIA")
        >>> balance = await provider.get_balance(wallet.id)
    """
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type identifier."""
        pass
    
    @property
    @abstractmethod
    def supported_blockchains(self) -> list[str]:
        """Return list of supported blockchain identifiers."""
        pass
    
    # =========================================================================
    # Wallet Set Operations
    # =========================================================================
    
    @abstractmethod
    async def list_wallet_sets(self) -> list[WalletSetInfo]:
        """List all wallet sets/groups."""
        pass
    
    @abstractmethod
    async def create_wallet_set(self, name: str) -> WalletSetInfo:
        """Create a new wallet set/group."""
        pass
    
    @abstractmethod
    async def get_wallet_set(self, wallet_set_id: str) -> WalletSetInfo | None:
        """Get a wallet set by ID."""
        pass
    
    # =========================================================================
    # Wallet Operations
    # =========================================================================
    
    @abstractmethod
    async def list_wallets(self, wallet_set_id: str | None = None) -> list[WalletInfo]:
        """List wallets, optionally filtered by wallet set."""
        pass
    
    @abstractmethod
    async def create_wallet(
        self,
        wallet_set_id: str,
        blockchain: str,
        name: str | None = None,
    ) -> WalletInfo:
        """Create a new wallet in a wallet set."""
        pass
    
    @abstractmethod
    async def get_wallet(self, wallet_id: str) -> WalletInfo | None:
        """Get a wallet by ID."""
        pass
    
    # =========================================================================
    # Balance Operations
    # =========================================================================
    
    @abstractmethod
    async def get_balances(self, wallet_id: str) -> list[TokenBalance]:
        """Get all token balances for a wallet."""
        pass
    
    async def get_usdc_balance(self, wallet_id: str) -> Decimal:
        """Get USDC balance for a wallet. Convenience method."""
        balances = await self.get_balances(wallet_id)
        for balance in balances:
            if balance.token_symbol.upper() == "USDC":
                return balance.amount
        return Decimal("0")
    
    # =========================================================================
    # Transfer Operations
    # =========================================================================
    
    @abstractmethod
    async def transfer(
        self,
        wallet_id: str,
        recipient: str,
        amount: Decimal,
        token_symbol: str = "USDC",
        idempotency_key: str | None = None,
    ) -> TransactionResult:
        """Transfer tokens from a wallet to a recipient address."""
        pass
    
    @abstractmethod
    async def get_transaction(self, transaction_id: str) -> TransactionResult | None:
        """Get transaction status by ID."""
        pass
    
    # =========================================================================
    # Smart Contract Operations (for cross-chain, etc.)
    # =========================================================================
    
    @abstractmethod
    async def execute_contract(
        self,
        wallet_id: str,
        contract_address: str,
        abi: list[dict[str, Any]],
        function_name: str,
        params: list[Any],
        value: str = "0",
    ) -> ContractCallResult:
        """Execute a smart contract function."""
        pass
    
    # =========================================================================
    # Provider-Specific Operations
    # =========================================================================
    
    def get_usdc_token_id(self, blockchain: str) -> str | None:
        """
        Get the USDC token ID for a blockchain.
        
        Override in provider implementations if needed.
        """
        return None
    
    def get_usdc_contract_address(self, blockchain: str) -> str | None:
        """
        Get the USDC contract address for a blockchain.
        
        Override in provider implementations if needed.
        """
        return None
    
    async def close(self) -> None:
        """Clean up provider resources. Override if needed."""
        pass


class CrossChainProvider(ABC):
    """
    Optional interface for providers that support cross-chain transfers.
    
    Not all providers support this - Circle has CCTP, others may have
    different mechanisms or none at all.
    """
    
    @abstractmethod
    async def transfer_cross_chain(
        self,
        wallet_id: str,
        recipient: str,
        amount: Decimal,
        source_chain: str,
        destination_chain: str,
    ) -> TransactionResult:
        """Transfer tokens across chains."""
        pass
    
    @abstractmethod
    def supports_cross_chain(self, source: str, destination: str) -> bool:
        """Check if cross-chain transfer is supported between two chains."""
        pass
