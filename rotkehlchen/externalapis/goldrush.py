import logging
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests
from requests.auth import HTTPBasicAuth

from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_transaction
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import iso8601ts_to_timestamp
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

GOLDRUSH_BASE_URL: Final = 'https://api.covalenthq.com/v1'
GOLDRUSH_PAGINATION_LIMIT: Final = 100
# Free tier: 4 requests/second → 0.25 seconds between requests
GOLDRUSH_RATE_LIMIT_INTERVAL: Final = 0.25

CHAINID_TO_GOLDRUSH_SLUG: Final[dict[ChainID, str]] = {
    ChainID.ETHEREUM: 'eth-mainnet',
    ChainID.OPTIMISM: 'optimism-mainnet',
    ChainID.POLYGON_POS: 'matic-mainnet',
    ChainID.ARBITRUM_ONE: 'arbitrum-mainnet',
    ChainID.BASE: 'base-mainnet',
    ChainID.GNOSIS: 'gnosis-mainnet',
    ChainID.BINANCE_SC: 'bsc-mainnet',
    ChainID.SCROLL: 'scroll-mainnet',
    ChainID.AVALANCHE: 'avalanche-mainnet',
    ChainID.ZKSYNC_ERA: 'zksync-mainnet',
}


class GoldRush(ExternalServiceWithApiKey, EtherscanLikeApi):
    """GoldRush (Covalent) API client. A single instance serves all EVM chains."""

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        ExternalServiceWithApiKey.__init__(
            self,
            database=database,
            service_name=ExternalService.GOLDRUSH,
        )
        EtherscanLikeApi.__init__(
            self,
            database=database,
            msg_aggregator=msg_aggregator,
            name='GoldRush',
            default_api_key=ApiKey(''),
            pagination_limit=GOLDRUSH_PAGINATION_LIMIT,
        )
        self._last_request_ts: float = 0.0

    def _get_slug(self, chain_id: ChainID) -> str:
        """Get the GoldRush chain slug for the given chain.

        May raise:
        - ChainNotSupported if the chain is not supported by GoldRush
        """
        if (slug := CHAINID_TO_GOLDRUSH_SLUG.get(chain_id)) is None:
            raise ChainNotSupported(f'GoldRush does not support {chain_id.name}')
        return slug

    @staticmethod
    def _get_url(chain_id: SUPPORTED_CHAIN_IDS) -> str:
        """Required by EtherscanLikeApi ABC. Returns base URL; not used by GoldRush's own
        _request() method which builds chain-specific paths directly."""
        return GOLDRUSH_BASE_URL

    def _get_api_key_for_chain(self, chain_id: ChainID) -> ApiKey | None:
        """GoldRush uses the same API key for all chains."""
        return self._get_api_key()

    @staticmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        """Required by EtherscanLikeApi ABC. Returns empty dict since GoldRush's own
        _request() method does not use the etherscan-style query format."""
        return {}

    def _request(
            self,
            path: str,
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Rate-limited GET request to the GoldRush API.

        May raise:
        - RemoteError if no API key is configured, the request fails, or the API returns an error
        """
        elapsed = time.monotonic() - self._last_request_ts
        sleep_time = GOLDRUSH_RATE_LIMIT_INTERVAL - elapsed
        if sleep_time > 0:
            gevent.sleep(sleep_time)

        api_key = self._get_api_key()
        if api_key is None:
            raise RemoteError('GoldRush API key is not configured')

        url = f'{GOLDRUSH_BASE_URL}{path}'
        log.debug(f'Querying GoldRush: {url} params={params}')
        try:
            response = self.session.get(
                url=url,
                params=params or {},
                auth=HTTPBasicAuth(api_key, ''),
                timeout=(30, 30),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'GoldRush API request failed: {e!s}') from e
        finally:
            self._last_request_ts = time.monotonic()

        if response.status_code != 200:
            raise RemoteError(
                f'GoldRush API request to {url} failed with HTTP status '
                f'{response.status_code}: {response.text}',
            )

        try:
            json_ret = response.json()
        except Exception as e:
            raise RemoteError(
                f'GoldRush API returned invalid JSON for {url}: {response.text}',
            ) from e

        if json_ret.get('error'):
            raise RemoteError(
                f'GoldRush API error: {json_ret.get("error_message", "unknown error")}',
            )

        return json_ret

    def _paginate(
            self,
            path: str,
            params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Collect all pages from a GoldRush paginated endpoint (query-param pagination).

        Used for balances, transfers, NFTs, and pricing endpoints which accept
        `page-number` and `page-size` as query parameters.

        May raise:
        - RemoteError if any page request fails
        """
        all_items: list[dict[str, Any]] = []
        page_number = 0
        request_params = dict(params or {})
        request_params['page-size'] = str(GOLDRUSH_PAGINATION_LIMIT)

        while True:
            request_params['page-number'] = str(page_number)
            response = self._request(path=path, params=request_params)
            data = response.get('data') or {}
            items = data.get('items') or []
            all_items.extend(items)

            pagination = data.get('pagination') or {}
            if not pagination.get('has_more', False):
                break

            page_number += 1

        return all_items

    def _paginate_v3_transactions(
            self,
            path: str,
            params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Collect all pages from a GoldRush transactions_v3 endpoint.

        The v3 endpoint embeds the page number in the URL path
        (`/transactions_v3/page/{page}/`) rather than as a query parameter.

        May raise:
        - RemoteError if any page request fails
        """
        all_items: list[dict[str, Any]] = []
        page_number = 0
        request_params = dict(params or {})
        request_params['page-size'] = str(GOLDRUSH_PAGINATION_LIMIT)

        while True:
            response = self._request(path=f'{path}page/{page_number}/', params=request_params)
            data = response.get('data') or {}
            items = data.get('items') or []
            all_items.extend(items)

            pagination = data.get('pagination') or {}
            if not pagination.get('has_more', False):
                break

            page_number += 1

        return all_items

    @staticmethod
    def _goldrush_tx_to_etherscan_fmt(item: dict[str, Any]) -> dict[str, Any]:
        """Convert a GoldRush transaction item to an Etherscan-compatible dict.

        May raise:
        - KeyError if required fields are missing
        """
        from eth_utils import to_checksum_address

        to_addr = item.get('to_address')
        return {
            'hash': item['tx_hash'],
            'from': to_checksum_address(item['from_address']),
            'to': to_checksum_address(to_addr) if to_addr else '',
            'value': str(item.get('value', '0')),
            'gas': str(item.get('gas_offered', 0)),
            'gasUsed': str(item.get('gas_spent', 0)),
            'gasPrice': str(item.get('gas_price', 0)),
            'nonce': str(item.get('nonce', 0)),
            'blockNumber': str(item.get('block_height', 0)),
            'timeStamp': str(int(iso8601ts_to_timestamp(item['block_signed_at']))),
            'isError': '0' if item.get('successful', True) else '1',
            'input': item.get('input', '0x') or '0x',
        }

    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Get transactions for an account from GoldRush.

        For 'txlistinternal', raises RemoteError since GoldRush has no internal tx endpoint
        (so _try_indexers falls through to the next indexer).

        Supports block-range filtering via the `starting-block` and `ending-block`
        query parameters. Timestamp ranges must be pre-converted to blocks by the
        caller (e.g. via `maybe_timestamp_to_block_range`) before being passed here.

        May raise:
        - RemoteError if the action is 'txlistinternal', or if the API request fails
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        if action == 'txlistinternal':
            raise RemoteError('GoldRush does not support internal transaction listing')

        if account is None:
            yield []
            return

        slug = self._get_slug(chain_id)
        params: dict[str, Any] = {}

        if isinstance(period_or_hash, TimestampOrBlockRange):
            if period_or_hash.range_type == 'blocks':
                params['starting-block'] = str(period_or_hash.from_value)
                params['ending-block'] = str(period_or_hash.to_value)
            # timestamp ranges should have been converted to blocks upstream;
            # if not, we fall back to fetching all transactions

        items = self._paginate_v3_transactions(
            path=f'/{slug}/address/{account}/transactions_v3/',
            params=params if params else None,
        )

        transactions: list[EvmTransaction] = []
        for item in items:
            try:
                etherscan_fmt = self._goldrush_tx_to_etherscan_fmt(item)
                tx, _ = deserialize_evm_transaction(
                    data=etherscan_fmt,
                    internal=False,
                    chain_id=chain_id,
                    evm_inquirer=None,
                    indexer=self,
                )
                transactions.append(tx)
            except (DeserializationError, KeyError) as e:
                self.msg_aggregator.add_warning(
                    f'Failed to deserialize GoldRush transaction for {account} '
                    f'on {chain_id.name}: {e!s}',
                )
                continue

        yield transactions

    def get_token_transaction_hashes(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[EVMTxHash]]:
        """Get ERC-20 transfer transaction hashes for an account from GoldRush.

        Supports optional block range filtering via `starting-block` / `ending-block`
        query parameters on the transfers_v2 endpoint.

        May raise:
        - RemoteError if the API request fails
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        slug = self._get_slug(chain_id)
        params: dict[str, Any] = {}
        if from_block is not None:
            params['starting-block'] = str(from_block)
        if to_block is not None:
            params['ending-block'] = str(to_block)

        items = self._paginate(
            path=f'/{slug}/address/{account}/transfers_v2/',
            params=params if params else None,
        )

        hashes: list[EVMTxHash] = []
        for item in items:
            try:
                tx_hash = deserialize_evm_tx_hash(item['tx_hash'])
                hashes.append(tx_hash)
            except (DeserializationError, KeyError) as e:
                log.error(
                    f'Failed to read GoldRush tx hash for {account} on {chain_id.name}: {e!s}',
                )
                continue

        yield hashes

    def get_blocknumber_by_time(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            ts: Timestamp,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Not supported by GoldRush — raises RemoteError so _try_indexers tries next indexer."""
        raise RemoteError('GoldRush does not support get_blocknumber_by_time')

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """Not supported by GoldRush — raises RemoteError so _try_indexers tries next indexer."""
        raise RemoteError('GoldRush does not support L1 fee queries')

