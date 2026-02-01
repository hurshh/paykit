"""
Circle wallet provider implementation.

This module implements the WalletProvider interface for Circle's
Developer-Controlled Wallets API.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from paykit.core.cctp_constants import USDC_ADDRESSES
from paykit.core.exceptions import ConfigurationError, NetworkError, WalletError
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

# Circle SDK imports
try:
    from circle.web3 import developer_controlled_wallets, utils as circle_utils
    CIRCLE_SDK_AVAILABLE = True
except ImportError:
    CIRCLE_SDK_AVAILABLE = False
    developer_controlled_wallets = None
    circle_utils = None


@dataclass
class CircleConfig(ProviderConfig):
    """Circle-specific configuration."""
    entity_secret: str = ""
    # Circle-specific options
    auto_generate_entity_secret: bool = True


# Mapping from our blockchain names to Circle's blockchain names
BLOCKCHAIN_MAPPING = {
    # Testnets
    "ETH-SEPOLIA": "ETH-SEPOLIA",
    "MATIC-AMOY": "MATIC-AMOY", 
    "ARB-SEPOLIA": "ARB-SEPOLIA",
    "BASE-SEPOLIA": "BASE-SEPOLIA",
    "AVAX-FUJI": "AVAX-FUJI",
    "SOL-DEVNET": "SOL-DEVNET",
    "ARC-TESTNET": "ARC-TESTNET",
    # Mainnets
    "ETH": "ETH",
    "MATIC": "MATIC",
    "ARB": "ARB",
    "BASE": "BASE",
    "AVAX": "AVAX",
    "SOL": "SOL",
}

# Reverse mapping
CIRCLE_TO_STANDARD = {v: k for k, v in BLOCKCHAIN_MAPPING.items()}


def _map_transaction_state(circle_state: str) -> TransactionState:
    """Map Circle transaction states to our universal states."""
    state_map = {
        "INITIATED": TransactionState.PENDING,
        "PENDING_RISK_SCREENING": TransactionState.PENDING,
        "QUEUED": TransactionState.PENDING,
        "SENT": TransactionState.PENDING,
        "CONFIRMED": TransactionState.CONFIRMED,
        "COMPLETE": TransactionState.COMPLETE,
        "FAILED": TransactionState.FAILED,
        "CANCELLED": TransactionState.CANCELLED,
        "DENIED": TransactionState.FAILED,
    }
    return state_map.get(circle_state.upper(), TransactionState.PENDING)


class CircleProvider(WalletProvider, CrossChainProvider):
    """
    Circle Developer-Controlled Wallets provider.
    
    This provider uses Circle's Web3 Services API to manage wallets
    and execute transactions.
    
    Example:
        >>> config = CircleConfig(api_key="...", entity_secret="...")
        >>> provider = CircleProvider(config)
        >>> wallet = await provider.create_wallet("set-id", "ETH-SEPOLIA")
    """
    
    def __init__(self, config: CircleConfig) -> None:
        if not CIRCLE_SDK_AVAILABLE:
            raise ConfigurationError(
                "Circle SDK not installed. Run: pip install circle-developer-controlled-wallets"
            )
        
        self._config = config
        
        try:
            self._client = circle_utils.init_developer_controlled_wallets_client(
                api_key=config.api_key,
                entity_secret=config.entity_secret,
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize Circle client: {e}",
                details={"error": str(e)},
            ) from e
        
        # Initialize API instances
        self._wallet_sets_api = developer_controlled_wallets.WalletSetsApi(self._client)
        self._wallets_api = developer_controlled_wallets.WalletsApi(self._client)
        self._transactions_api = developer_controlled_wallets.TransactionsApi(self._client)
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CIRCLE
    
    @property
    def supported_blockchains(self) -> list[str]:
        return list(BLOCKCHAIN_MAPPING.keys())
    
    def _get_ciphertext(self) -> str:
        """Generate entity secret ciphertext for signing."""
        return circle_utils.generate_entity_secret_ciphertext(
            api_key=self._config.api_key,
            entity_secret_hex=self._config.entity_secret,
        )
    
    def _to_circle_blockchain(self, blockchain: str) -> str:
        """Convert standard blockchain name to Circle format."""
        return BLOCKCHAIN_MAPPING.get(blockchain.upper(), blockchain)
    
    # =========================================================================
    # Wallet Set Operations
    # =========================================================================
    
    async def list_wallet_sets(self) -> list[WalletSetInfo]:
        try:
            response = self._wallet_sets_api.get_wallet_sets()
            result = []
            
            for ws in response.data.wallet_sets:
                ws_data = ws.to_dict()
                result.append(WalletSetInfo(
                    id=ws_data.get("id", ""),
                    name=ws_data.get("name", ""),
                    custody_type=ws_data.get("custodyType", "DEVELOPER"),
                    provider=ProviderType.CIRCLE,
                    raw=ws_data,
                ))
            
            return result
            
        except developer_controlled_wallets.ApiException as e:
            raise WalletError(f"Failed to list wallet sets: {e}")
    
    async def create_wallet_set(self, name: str) -> WalletSetInfo:
        try:
            ciphertext = self._get_ciphertext()
            idempotency_key = str(uuid.uuid4())
            
            request = developer_controlled_wallets.CreateWalletSetRequest.from_dict({
                "name": name,
                "idempotencyKey": idempotency_key,
                "entitySecretCiphertext": ciphertext,
            })
            response = self._wallet_sets_api.create_wallet_set(request)
            
            ws_data = response.data.wallet_set.to_dict()
            return WalletSetInfo(
                id=ws_data.get("id", ""),
                name=ws_data.get("name", ""),
                custody_type=ws_data.get("custodyType", "DEVELOPER"),
                provider=ProviderType.CIRCLE,
                raw=ws_data,
            )
            
        except developer_controlled_wallets.ApiException as e:
            raise WalletError(f"Failed to create wallet set: {e}")
    
    async def get_wallet_set(self, wallet_set_id: str) -> WalletSetInfo | None:
        try:
            response = self._wallet_sets_api.get_wallet_set(wallet_set_id)
            ws_data = response.data.wallet_set.actual_instance.to_dict()
            return WalletSetInfo(
                id=ws_data.get("id", ""),
                name=ws_data.get("name", ""),
                custody_type=ws_data.get("custodyType", "DEVELOPER"),
                provider=ProviderType.CIRCLE,
                raw=ws_data,
            )
        except developer_controlled_wallets.ApiException:
            return None
    
    # =========================================================================
    # Wallet Operations
    # =========================================================================
    
    async def list_wallets(self, wallet_set_id: str | None = None) -> list[WalletInfo]:
        try:
            kwargs: dict[str, Any] = {}
            if wallet_set_id:
                kwargs["wallet_set_id"] = wallet_set_id
            
            response = self._wallets_api.get_wallets(**kwargs)
            result = []
            
            for wallet in response.data.wallets:
                w_data = wallet.actual_instance.to_dict()
                result.append(WalletInfo(
                    id=w_data.get("id", ""),
                    address=w_data.get("address", ""),
                    blockchain=w_data.get("blockchain", ""),
                    name=w_data.get("name"),
                    state=w_data.get("state", "LIVE"),
                    provider=ProviderType.CIRCLE,
                    raw=w_data,
                ))
            
            return result
            
        except developer_controlled_wallets.ApiException as e:
            raise WalletError(f"Failed to list wallets: {e}")
    
    async def create_wallet(
        self,
        wallet_set_id: str,
        blockchain: str,
        name: str | None = None,
    ) -> WalletInfo:
        try:
            ciphertext = self._get_ciphertext()
            idempotency_key = str(uuid.uuid4())
            circle_blockchain = self._to_circle_blockchain(blockchain)
            
            request = developer_controlled_wallets.CreateWalletRequest.from_dict({
                "walletSetId": wallet_set_id,
                "blockchains": [circle_blockchain],
                "count": 1,
                "accountType": "EOA",
                "idempotencyKey": idempotency_key,
                "entitySecretCiphertext": ciphertext,
            })
            response = self._wallets_api.create_wallet(request)
            
            wallet = response.data.wallets[0]
            w_data = wallet.actual_instance.to_dict()
            
            return WalletInfo(
                id=w_data.get("id", ""),
                address=w_data.get("address", ""),
                blockchain=w_data.get("blockchain", ""),
                name=name,
                state=w_data.get("state", "LIVE"),
                provider=ProviderType.CIRCLE,
                raw=w_data,
            )
            
        except developer_controlled_wallets.ApiException as e:
            raise WalletError(f"Failed to create wallet: {e}")
    
    async def get_wallet(self, wallet_id: str) -> WalletInfo | None:
        try:
            response = self._wallets_api.get_wallet(wallet_id)
            w_data = response.data.wallet.actual_instance.to_dict()
            return WalletInfo(
                id=w_data.get("id", ""),
                address=w_data.get("address", ""),
                blockchain=w_data.get("blockchain", ""),
                name=w_data.get("name"),
                state=w_data.get("state", "LIVE"),
                provider=ProviderType.CIRCLE,
                raw=w_data,
            )
        except developer_controlled_wallets.ApiException:
            return None
    
    # =========================================================================
    # Balance Operations
    # =========================================================================
    
    async def get_balances(self, wallet_id: str) -> list[TokenBalance]:
        try:
            response = self._wallets_api.list_wallet_balance(wallet_id)
            result = []
            
            for tb in response.data.token_balances:
                b_data = tb.to_dict()
                token_data = b_data.get("token", {})
                result.append(TokenBalance(
                    token_id=token_data.get("id", ""),
                    token_symbol=token_data.get("symbol", ""),
                    amount=Decimal(b_data.get("amount", "0")),
                    blockchain=token_data.get("blockchain", ""),
                    raw=b_data,
                ))
            
            return result
            
        except developer_controlled_wallets.ApiException as e:
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
        try:
            # Find USDC token ID for this wallet
            balances = await self.get_balances(wallet_id)
            token_id = None
            for balance in balances:
                if balance.token_symbol.upper() in ("USDC", "USDC-TESTNET"):
                    token_id = balance.token_id
                    break
            
            if not token_id:
                raise WalletError("USDC token not found in wallet")
            
            ciphertext = self._get_ciphertext()
            if not idempotency_key:
                idempotency_key = str(uuid.uuid4())
            
            request = developer_controlled_wallets.CreateTransferTransactionForDeveloperRequest.from_dict({
                "idempotencyKey": idempotency_key,
                "entitySecretCiphertext": ciphertext,
                "walletId": wallet_id,
                "tokenId": token_id,
                "destinationAddress": recipient,
                "amounts": [str(amount)],
                "feeLevel": "MEDIUM",
            })
            response = self._transactions_api.create_developer_transaction_transfer(request)
            
            tx_data = response.data.to_dict()
            return TransactionResult(
                id=tx_data.get("id", ""),
                state=_map_transaction_state(tx_data.get("state", "PENDING")),
                tx_hash=tx_data.get("txHash"),
                amount=amount,
                raw=tx_data,
            )
            
        except developer_controlled_wallets.ApiException as e:
            raise WalletError(f"Failed to create transfer: {e}")
    
    async def get_transaction(self, transaction_id: str) -> TransactionResult | None:
        try:
            response = self._transactions_api.get_transaction(transaction_id)
            tx_data = response.data.transaction.to_dict()
            return TransactionResult(
                id=tx_data.get("id", ""),
                state=_map_transaction_state(tx_data.get("state", "PENDING")),
                tx_hash=tx_data.get("txHash"),
                raw=tx_data,
            )
        except developer_controlled_wallets.ApiException:
            return None
    
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
        try:
            ciphertext = self._get_ciphertext()
            idempotency_key = str(uuid.uuid4())
            
            # Build ABI function signature from the ABI
            abi_signature = self._build_abi_signature(abi, function_name)
            
            request = developer_controlled_wallets.CreateContractExecutionTransactionForDeveloperRequest.from_dict({
                "idempotencyKey": idempotency_key,
                "entitySecretCiphertext": ciphertext,
                "walletId": wallet_id,
                "contractAddress": contract_address,
                "abiFunctionSignature": abi_signature,
                "abiParameters": [str(p) for p in params],
                "feeLevel": "MEDIUM",
            })
            response = self._transactions_api.create_developer_transaction_contract_execution(request)
            
            tx_data = response.data.to_dict()
            return ContractCallResult(
                id=tx_data.get("id", ""),
                state=_map_transaction_state(tx_data.get("state", "PENDING")),
                tx_hash=tx_data.get("txHash"),
                raw=tx_data,
            )
            
        except developer_controlled_wallets.ApiException as e:
            raise WalletError(f"Failed to execute contract: {e}")
    
    def _build_abi_signature(self, abi: list[dict[str, Any]], function_name: str) -> str:
        """Build function signature from ABI."""
        for item in abi:
            if item.get("type") == "function" and item.get("name") == function_name:
                inputs = item.get("inputs", [])
                param_types = ",".join(inp.get("type", "") for inp in inputs)
                return f"{function_name}({param_types})"
        return function_name
    
    # =========================================================================
    # Cross-Chain Operations (CCTP)
    # =========================================================================
    
    async def transfer_cross_chain(
        self,
        wallet_id: str,
        recipient: str,
        amount: Decimal,
        source_chain: str,
        destination_chain: str,
    ) -> TransactionResult:
        """
        Transfer USDC across chains using Circle's CCTP.
        
        This is a simplified interface - the full CCTP flow is handled
        by the GatewayAdapter in the protocols module.
        """
        # CCTP requires multiple steps (approve, burn, attest, mint)
        # This method delegates to the gateway adapter
        raise NotImplementedError(
            "Cross-chain transfers should use the GatewayAdapter protocol. "
            "Use client.pay() with destination_chain parameter."
        )
    
    def supports_cross_chain(self, source: str, destination: str) -> bool:
        """Check if CCTP supports this chain pair."""
        cctp_chains = {
            "ETH", "ETH-SEPOLIA",
            "MATIC", "MATIC-AMOY",
            "ARB", "ARB-SEPOLIA",
            "BASE", "BASE-SEPOLIA",
            "AVAX", "AVAX-FUJI",
            "ARC-TESTNET",
        }
        return source.upper() in cctp_chains and destination.upper() in cctp_chains
    
    # =========================================================================
    # Provider-Specific Methods
    # =========================================================================
    
    def get_usdc_token_id(self, blockchain: str) -> str | None:
        """Get USDC token ID - requires querying a wallet."""
        # Circle doesn't have static token IDs, they're wallet-specific
        return None
    
    def get_usdc_contract_address(self, blockchain: str) -> str | None:
        """Get USDC contract address for a blockchain."""
        return USDC_ADDRESSES.get(blockchain.upper())
