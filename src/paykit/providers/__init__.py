"""
PayKit Wallet Providers.

This module provides a vendor-agnostic interface for wallet infrastructure.
Currently supports Circle, with Coinbase support coming soon.

Usage:
    >>> from paykit.providers import get_provider, CircleProvider, ProviderType
    >>> 
    >>> # Get default provider (Circle)
    >>> provider = get_provider()
    >>> 
    >>> # Or specify provider explicitly
    >>> provider = get_provider(ProviderType.CIRCLE, api_key="...", entity_secret="...")
    >>> 
    >>> # Use the provider
    >>> wallet = await provider.create_wallet("set-id", "ETH-SEPOLIA")
"""

from __future__ import annotations

import os
from typing import Any

from paykit.providers.base import (
    ContractCallResult,
    CrossChainProvider,
    ProviderConfig,
    ProviderType,
    TokenBalance,
    TransactionResult,
    TransactionState,
    WalletInfo,
    WalletProvider,
    WalletSetInfo,
)
from paykit.providers.circle import CircleConfig, CircleProvider
from paykit.providers.coinbase import CoinbaseConfig, CoinbaseProvider


# Provider registry
_PROVIDERS: dict[ProviderType, type[WalletProvider]] = {
    ProviderType.CIRCLE: CircleProvider,
    ProviderType.COINBASE: CoinbaseProvider,
}


def get_provider(
    provider_type: ProviderType | str | None = None,
    **kwargs: Any,
) -> WalletProvider:
    """
    Get a wallet provider instance.
    
    Args:
        provider_type: Provider type (defaults to CIRCLE, or reads from PAYKIT_PROVIDER env var)
        **kwargs: Provider-specific configuration options
            For Circle: api_key, entity_secret
            For Coinbase: api_key, api_secret
    
    Returns:
        Configured WalletProvider instance
    
    Example:
        >>> # Auto-detect from environment
        >>> provider = get_provider()
        >>> 
        >>> # Explicit Circle provider
        >>> provider = get_provider(
        ...     ProviderType.CIRCLE,
        ...     api_key="your-api-key",
        ...     entity_secret="your-entity-secret"
        ... )
    """
    # Determine provider type
    if provider_type is None:
        env_provider = os.environ.get("PAYKIT_PROVIDER", "circle").lower()
        provider_type = ProviderType(env_provider)
    elif isinstance(provider_type, str):
        provider_type = ProviderType(provider_type.lower())
    
    # Get provider class
    provider_class = _PROVIDERS.get(provider_type)
    if provider_class is None:
        raise ValueError(f"Unknown provider type: {provider_type}")
    
    # Build configuration
    if provider_type == ProviderType.CIRCLE:
        config = _build_circle_config(**kwargs)
        return CircleProvider(config)
    elif provider_type == ProviderType.COINBASE:
        config = _build_coinbase_config(**kwargs)
        return CoinbaseProvider(config)
    else:
        raise ValueError(f"Provider not implemented: {provider_type}")


def _build_circle_config(**kwargs: Any) -> CircleConfig:
    """Build Circle configuration from kwargs and environment."""
    return CircleConfig(
        api_key=kwargs.get("api_key") or os.environ.get("CIRCLE_API_KEY", ""),
        entity_secret=kwargs.get("entity_secret") or os.environ.get("ENTITY_SECRET", ""),
        environment=kwargs.get("environment", "testnet"),
        timeout=kwargs.get("timeout", 30.0),
    )


def _build_coinbase_config(**kwargs: Any) -> CoinbaseConfig:
    """Build Coinbase configuration from kwargs and environment."""
    return CoinbaseConfig(
        api_key=kwargs.get("api_key") or os.environ.get("COINBASE_API_KEY", ""),
        api_secret=kwargs.get("api_secret") or os.environ.get("COINBASE_API_SECRET", ""),
        environment=kwargs.get("environment", "testnet"),
        timeout=kwargs.get("timeout", 30.0),
    )


def register_provider(
    provider_type: ProviderType,
    provider_class: type[WalletProvider],
) -> None:
    """
    Register a custom wallet provider.
    
    This allows extending PayKit with custom providers.
    
    Args:
        provider_type: Unique provider identifier
        provider_class: Provider class implementing WalletProvider
    
    Example:
        >>> class MyProvider(WalletProvider):
        ...     # Implementation
        ...     pass
        >>> 
        >>> register_provider(ProviderType("my-provider"), MyProvider)
    """
    _PROVIDERS[provider_type] = provider_class


def list_providers() -> list[ProviderType]:
    """List all registered provider types."""
    return list(_PROVIDERS.keys())


__all__ = [
    # Factory
    "get_provider",
    "register_provider",
    "list_providers",
    # Base types
    "WalletProvider",
    "CrossChainProvider",
    "ProviderType",
    "ProviderConfig",
    "WalletInfo",
    "WalletSetInfo",
    "TokenBalance",
    "TransactionResult",
    "TransactionState",
    "ContractCallResult",
    # Circle
    "CircleProvider",
    "CircleConfig",
    # Coinbase
    "CoinbaseProvider",
    "CoinbaseConfig",
]
