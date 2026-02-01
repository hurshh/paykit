"""
Coinbase wallet provider implementation.

This module implements the WalletProvider interface for Coinbase's
Developer Platform (CDP) SDK.

Requires: pip install cdp-sdk
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from paykit.core.exceptions import ConfigurationError, WalletError
from paykit.providers.base import (
    ContractCallResult,
    ProviderConfig,
    ProviderType,
    TokenBalance,
    TransactionResult,
    TransactionState,
    WalletInfo,
    WalletProvider,
    WalletSetInfo,
)

# Coinbase CDP SDK imports
try:
    from cdp import CdpClient
    CDP_SDK_AVAILABLE = True
except ImportError:
    CDP_SDK_AVAILABLE = False
    CdpClient = None


@dataclass
class CoinbaseConfig(ProviderConfig):
    """Coinbase-specific configuration."""
    api_secret: str = ""
    wallet_secret: str = ""
    # Environment variables used by CDP SDK
    # CDP_API_KEY_ID, CDP_API_KEY_SECRET, CDP_WALLET_SECRET


# Blockchain mapping: PayKit names -> Coinbase network names
BLOCKCHAIN_MAPPING = {
    # Testnets
    "ETH-SEPOLIA": "ethereum-sepolia",
    "BASE-SEPOLIA": "base-sepolia",
    "ARB-SEPOLIA": "arbitrum-sepolia",
    "SOL-DEVNET": "solana-devnet",
    # Mainnets
    "ETH": "ethereum",
    "BASE": "base",
    "ARB": "arbitrum",
    "SOL": "solana",
    "MATIC": "polygon",
    "AVAX": "avalanche",
}

# Reverse mapping
COINBASE_TO_STANDARD = {v: k for k, v in BLOCKCHAIN_MAPPING.items()}


def _map_blockchain_type(blockchain: str) -> str:
    """Determine if blockchain is EVM or Solana."""
    sol_chains = {"SOL", "SOL-DEVNET", "solana", "solana-devnet"}
    return "solana" if blockchain.upper() in sol_chains or blockchain.lower() in sol_chains else "evm"


class CoinbaseProvider(WalletProvider):
    """
    Coinbase Developer Platform (CDP) provider.
    
    This provider uses Coinbase's CDP SDK to manage accounts
    and execute transactions.
    
    Note: Coinbase uses "accounts" instead of "wallets" and doesn't have
    the concept of "wallet sets". We simulate wallet sets using account naming.
    
    Example:
        >>> config = CoinbaseConfig(
        ...     api_key="your-api-key-id",
        ...     api_secret="your-api-key-secret",
        ...     wallet_secret="your-wallet-secret"
        ... )
        >>> provider = CoinbaseProvider(config)
        >>> wallet = await provider.create_wallet("set-id", "BASE-SEPOLIA")
    
    Environment Variables:
        CDP_API_KEY_ID: Coinbase API Key ID
        CDP_API_KEY_SECRET: Coinbase API Key Secret
        CDP_WALLET_SECRET: Coinbase Wallet Secret for signing
    """
    
    def __init__(self, config: CoinbaseConfig) -> None:
        if not CDP_SDK_AVAILABLE:
            raise ConfigurationError(
                "Coinbase CDP SDK not installed. Run: pip install cdp-sdk"
            )
        
        self._config = config
        self._client: CdpClient | None = None
        
        # Track created accounts (Coinbase doesn't have list_accounts)
        self._accounts: dict[str, WalletInfo] = {}
        self._wallet_sets: dict[str, WalletSetInfo] = {}
    
    async def _ensure_client(self) -> CdpClient:
        """Lazily initialize the CDP client."""
        if self._client is None:
            try:
                # CDP SDK reads from env vars or we can pass explicitly
                if self._config.api_key and self._config.api_secret:
                    self._client = CdpClient(
                        api_key_id=self._config.api_key,
                        api_key_secret=self._config.api_secret,
                        wallet_secret=self._config.wallet_secret,
                    )
                else:
                    # Let CDP SDK read from environment
                    self._client = CdpClient()
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to initialize Coinbase CDP client: {e}",
                    details={"error": str(e)},
                ) from e
        return self._client
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.COINBASE
    
    @property
    def supported_blockchains(self) -> list[str]:
        return list(BLOCKCHAIN_MAPPING.keys())
    
    def _to_coinbase_network(self, blockchain: str) -> str:
        """Convert standard blockchain name to Coinbase network name."""
        return BLOCKCHAIN_MAPPING.get(blockchain.upper(), blockchain.lower())
    
    def _from_coinbase_network(self, network: str) -> str:
        """Convert Coinbase network name to standard blockchain name."""
        return COINBASE_TO_STANDARD.get(network, network.upper())
    
    # =========================================================================
    # Wallet Set Operations
    # =========================================================================
    
    async def list_wallet_sets(self) -> list[WalletSetInfo]:
        """
        List all wallet sets.
        
        Note: Coinbase doesn't have wallet sets, so we simulate them
        using a local registry based on account naming conventions.
        """
        return list(self._wallet_sets.values())
    
    async def create_wallet_set(self, name: str) -> WalletSetInfo:
        """
        Create a new wallet set.
        
        Note: Coinbase doesn't have wallet sets, so we simulate them
        by tracking them locally and using the set name as a prefix
        for account names.
        """
        import uuid
        wallet_set_id = f"coinbase-set-{uuid.uuid4().hex[:8]}"
        
        wallet_set = WalletSetInfo(
            id=wallet_set_id,
            name=name,
            custody_type="DEVELOPER",
            provider=ProviderType.COINBASE,
            raw={"simulated": True},
        )
        self._wallet_sets[wallet_set_id] = wallet_set
        return wallet_set
    
    async def get_wallet_set(self, wallet_set_id: str) -> WalletSetInfo | None:
        """Get a wallet set by ID."""
        return self._wallet_sets.get(wallet_set_id)
    
    # =========================================================================
    # Wallet Operations
    # =========================================================================
    
    async def list_wallets(self, wallet_set_id: str | None = None) -> list[WalletInfo]:
        """
        List wallets, optionally filtered by wallet set.
        
        Note: Returns wallets from local registry. Coinbase doesn't
        provide a list_accounts API, so we track created accounts.
        """
        if wallet_set_id:
            return [w for w in self._accounts.values() 
                    if w.raw.get("wallet_set_id") == wallet_set_id]
        return list(self._accounts.values())
    
    async def create_wallet(
        self,
        wallet_set_id: str,
        blockchain: str,
        name: str | None = None,
    ) -> WalletInfo:
        """
        Create a new wallet (account) in Coinbase.
        
        Args:
            wallet_set_id: Wallet set ID (used for naming convention)
            blockchain: Target blockchain (e.g., "BASE-SEPOLIA", "SOL-DEVNET")
            name: Optional account name
        """
        import uuid
        
        client = await self._ensure_client()
        chain_type = _map_blockchain_type(blockchain)
        network = self._to_coinbase_network(blockchain)
        
        # Generate a unique name if not provided
        account_name = name or f"paykit-{uuid.uuid4().hex[:8]}"
        
        try:
            async with client:
                if chain_type == "solana":
                    account = await client.solana.create_account(name=account_name)
                else:
                    account = await client.evm.create_account(name=account_name)
                
                wallet_info = WalletInfo(
                    id=account_name,  # Use name as ID since Coinbase uses addresses
                    address=account.address,
                    blockchain=blockchain,
                    name=account_name,
                    state="LIVE",
                    provider=ProviderType.COINBASE,
                    raw={
                        "wallet_set_id": wallet_set_id,
                        "network": network,
                        "chain_type": chain_type,
                    },
                )
                
                self._accounts[account_name] = wallet_info
                return wallet_info
                
        except Exception as e:
            raise WalletError(f"Failed to create Coinbase account: {e}")
    
    async def get_wallet(self, wallet_id: str) -> WalletInfo | None:
        """
        Get a wallet by ID (account name).
        
        First checks local registry, then tries to get from Coinbase.
        """
        # Check local registry first
        if wallet_id in self._accounts:
            return self._accounts[wallet_id]
        
        # Try to get/create from Coinbase
        client = await self._ensure_client()
        try:
            async with client:
                # Try EVM first
                try:
                    account = await client.evm.get_or_create_account(name=wallet_id)
                    wallet_info = WalletInfo(
                        id=wallet_id,
                        address=account.address,
                        blockchain="ETH",  # Default, will be updated on use
                        name=wallet_id,
                        state="LIVE",
                        provider=ProviderType.COINBASE,
                        raw={"chain_type": "evm"},
                    )
                    self._accounts[wallet_id] = wallet_info
                    return wallet_info
                except Exception:
                    pass
                
                # Try Solana
                try:
                    account = await client.solana.get_or_create_account(name=wallet_id)
                    wallet_info = WalletInfo(
                        id=wallet_id,
                        address=account.address,
                        blockchain="SOL",
                        name=wallet_id,
                        state="LIVE",
                        provider=ProviderType.COINBASE,
                        raw={"chain_type": "solana"},
                    )
                    self._accounts[wallet_id] = wallet_info
                    return wallet_info
                except Exception:
                    pass
                    
        except Exception:
            pass
        
        return None
    
    # =========================================================================
    # Balance Operations
    # =========================================================================
    
    async def get_balances(self, wallet_id: str) -> list[TokenBalance]:
        """
        Get all token balances for a wallet.
        
        Uses Coinbase's list_token_balances action.
        """
        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            raise WalletError(f"Wallet not found: {wallet_id}")
        
        client = await self._ensure_client()
        network = wallet.raw.get("network", self._to_coinbase_network(wallet.blockchain))
        chain_type = wallet.raw.get("chain_type", _map_blockchain_type(wallet.blockchain))
        
        try:
            async with client:
                if chain_type == "solana":
                    account = await client.solana.get_or_create_account(name=wallet_id)
                else:
                    account = await client.evm.get_or_create_account(name=wallet_id)
                
                # Get token balances
                balances = await account.list_token_balances(network=network)
                
                result = []
                for balance in balances:
                    result.append(TokenBalance(
                        token_id=balance.token.contract_address or balance.token.symbol,
                        token_symbol=balance.token.symbol,
                        amount=Decimal(str(balance.amount)),
                        blockchain=wallet.blockchain,
                        raw={"balance": balance},
                    ))
                
                return result
                
        except Exception as e:
            raise WalletError(f"Failed to get balances: {e}")
    
    # =========================================================================
    # Transfer Operations
    # =========================================================================
    
    async def transfer(
        self,
        wallet_id: str,
        recipient: str,
        amount: Decimal,
        token_symbol: str = "USDC",
        idempotency_key: str | None = None,
    ) -> TransactionResult:
        """
        Transfer tokens from a wallet to a recipient address.
        
        Uses Coinbase's account.transfer() method.
        """
        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            raise WalletError(f"Wallet not found: {wallet_id}")
        
        client = await self._ensure_client()
        network = wallet.raw.get("network", self._to_coinbase_network(wallet.blockchain))
        chain_type = wallet.raw.get("chain_type", _map_blockchain_type(wallet.blockchain))
        
        try:
            async with client:
                if chain_type == "solana":
                    account = await client.solana.get_or_create_account(name=wallet_id)
                else:
                    account = await client.evm.get_or_create_account(name=wallet_id)
                
                # Convert USDC amount to atomic units (6 decimals)
                if token_symbol.upper() == "USDC":
                    atomic_amount = int(amount * Decimal("1000000"))
                else:
                    # For ETH/SOL, use 18 decimals for ETH, 9 for SOL
                    if chain_type == "solana":
                        atomic_amount = int(amount * Decimal("1000000000"))  # 9 decimals
                    else:
                        atomic_amount = int(amount * Decimal("1000000000000000000"))  # 18 decimals
                
                # Execute transfer
                tx_hash = await account.transfer(
                    to=recipient,
                    amount=atomic_amount,
                    token=token_symbol.lower(),
                    network=network,
                )
                
                return TransactionResult(
                    id=tx_hash,
                    state=TransactionState.PENDING,
                    tx_hash=tx_hash,
                    amount=amount,
                    raw={"network": network, "token": token_symbol},
                )
                
        except Exception as e:
            raise WalletError(f"Failed to transfer: {e}")
    
    async def get_transaction(self, transaction_id: str) -> TransactionResult | None:
        """
        Get transaction status by ID (tx hash).
        
        Note: Coinbase CDP doesn't have a direct get_transaction API.
        You would typically use a blockchain RPC to check tx status.
        """
        # Return a basic result - in production you'd query the blockchain
        return TransactionResult(
            id=transaction_id,
            state=TransactionState.PENDING,
            tx_hash=transaction_id,
            raw={"note": "Use blockchain RPC to check actual status"},
        )
    
    # =========================================================================
    # Smart Contract Operations
    # =========================================================================
    
    async def execute_contract(
        self,
        wallet_id: str,
        contract_address: str,
        abi: list[dict[str, Any]],
        function_name: str,
        params: list[Any],
        value: str = "0",
    ) -> ContractCallResult:
        """
        Execute a smart contract function.
        
        Uses Coinbase's send_transaction for contract calls.
        """
        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            raise WalletError(f"Wallet not found: {wallet_id}")
        
        client = await self._ensure_client()
        network = wallet.raw.get("network", self._to_coinbase_network(wallet.blockchain))
        
        try:
            async with client:
                account = await client.evm.get_or_create_account(name=wallet_id)
                
                # Build the transaction data
                # This is a simplified version - in production you'd use web3.py to encode
                from cdp.evm_transaction_types import TransactionRequestEIP1559
                
                tx_hash = await client.evm.send_transaction(
                    address=account.address,
                    transaction=TransactionRequestEIP1559(
                        to=contract_address,
                        value=int(value),
                        data="0x",  # Would need to encode function call
                    ),
                    network=network,
                )
                
                return ContractCallResult(
                    id=tx_hash,
                    state=TransactionState.PENDING,
                    tx_hash=tx_hash,
                    raw={"network": network, "contract": contract_address},
                )
                
        except Exception as e:
            raise WalletError(f"Failed to execute contract: {e}")
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    async def close(self) -> None:
        """Clean up the CDP client."""
        self._client = None
