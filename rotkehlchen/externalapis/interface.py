from abc import ABC, abstractmethod
from collections.abc import Iterator
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    Timestamp,
)
from rotkehlchen.utils.interfaces import DBSetterMixin
from rotkehlchen.utils.misc import ts_now

# number of transactions to accumulate before yielding a batch to the caller
TRANSACTIONS_BATCH_NUM: Final = 10

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class HasChainActivity(Enum):
    """Classify the type of transaction first found in blockscout/etherscan.

    TRANSACTIONS means that the endpoint for transactions/internal transactions
    had entries, TOKENS means that the tokens endpoint had entries, BALANCE means
    that the address has a non-zero native asset balance and NONE means that no
    activity was found.
    """
    TRANSACTIONS = auto()
    TOKENS = auto()
    BALANCE = auto()
    NONE = auto()


class EvmIndexerInterface(ABC):
    """Abstract interface for EVM blockchain indexers.

    Defines the core contract that all indexers (Etherscan, Blockscout, Routescan, SQD)
    must implement. Only contains methods that every indexer is expected to support.

    Etherscan-specific methods (RPC proxies, contract inspection, timestamp-to-block
    conversion, etc.) live in EtherscanLikeApi and are dispatched via
    _try_etherscan_like_indexers in the node inquirer.
    """
    name: str

    @abstractmethod
    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            internal: bool,
            period: TimestampOrBlockRange | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Yields batches of transactions for an account.

        When internal is True, yields internal (trace) transactions.
        Indexers that don't support timestamp ranges should raise RemoteError
        to fall through to the next indexer.
        """

    @abstractmethod
    def get_token_transaction_hashes(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[EVMTxHash]]:
        """Get transaction hashes involving ERC20 token transfers for an account."""

    @abstractmethod
    def get_logs(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            contract_address: ChecksumEvmAddress,
            topics: list[str | None],
            from_block: int,
            to_block: int | str = 'latest',
            existing_events: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Get event logs by contract address and topics."""

    @abstractmethod
    def get_latest_block_number(self, chain_id: SUPPORTED_CHAIN_IDS) -> int:
        """Get the latest block number for a chain."""

    @abstractmethod
    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> 'HasChainActivity':
        """Check if an account has any on-chain activity."""


class ExternalServiceWithApiKey:
    """Interface for any ExternalService that has an API Key

    The reason why database is Optional is only for the initialization of cryptocompare to be able
    to happen without having the DB ready. That's since at the moment it happens at Rotkehlchen
    object initialization in order to be passed on to the Inquirer Singleton.

    The problem here is that at constructor of all other objects we need to be
    specifying that the DB is an object that is non optional and exists to satisfy type checkers.
    """

    def __init__(self, database: 'DBHandler', service_name: ExternalService) -> None:
        self.db = database
        self.api_key: ApiKey | None = None
        self.service_name = service_name
        self.last_ts = Timestamp(0)

    def _get_api_key(self) -> ApiKey | None:
        """A function to get the API key from the DB (if we have one initialized)"""
        if self.api_key and ts_now() - self.last_ts <= 120:
            return self.api_key

        if not self.db:
            return None

        # else query the DB
        credentials = self.db.get_external_service_credentials(self.service_name)
        self.last_ts = ts_now()
        # If we get here it means the api key is modified/saved
        self.api_key = credentials.api_key if credentials else None
        return self.api_key


class ExternalServiceWithApiKeyOptionalDB(ExternalServiceWithApiKey, DBSetterMixin):
    """An extension of ExternalServiceWithAPIKey where the DB is optional at initialization

    The reason why database is Optional is only for the initialization of some services like
    defillama and cryptocompare to be able to happen without having the DB ready.
    That's needed since it needs to be passed down to the Inquirer singleton before
    DB is ready.
    """
    def __init__(self, database: 'DBHandler|None', service_name: ExternalService) -> None:
        super().__init__(database=database, service_name=service_name)  # type: ignore  # we are aware of discrepancy
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy

    def _get_name(self) -> str:
        return str(self.service_name)


class ExternalServiceWithRecommendedApiKey(ExternalServiceWithApiKey):
    """An extension of ExternalServiceWithAPIKey for services where we recommend always
    using an API key and warn the user if it's missing.
    """
    def __init__(self, database: 'DBHandler', service_name: ExternalService) -> None:
        ExternalServiceWithApiKey.__init__(self, database=database, service_name=service_name)
        self.warning_given = False

    def _get_api_key(self) -> ApiKey | None:
        if (api_key := ExternalServiceWithApiKey._get_api_key(self)) is not None:
            return api_key

        self.maybe_warn_missing_key()
        return None

    def maybe_warn_missing_key(self) -> None:
        """Warns the user once if the Helius api key is missing."""
        if not self.warning_given:
            self.db.msg_aggregator.add_missing_key_message(self.service_name)
            self.warning_given = True
