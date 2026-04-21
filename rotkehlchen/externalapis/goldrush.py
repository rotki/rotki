import base64
import json
import logging
import secrets
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests
from eth_account import Account as EthAccount
from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi, HasChainActivity
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
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
    Price,
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

# x402 payment protocol — USDC on Base mainnet
X402_BASE_CHAIN_ID: Final = 8453
X402_USDC_CONTRACT: Final = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
X402_USDC_EIP712_NAME: Final = 'USD Coin'
X402_USDC_EIP712_VERSION: Final = '2'
X402_PAYMENT_EXPIRY_SECONDS: Final = 60
X402_SCHEME: Final = 'exact'
X402_VERSION: Final = 1

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
    ChainID.FANTOM: 'fantom-mainnet',
    ChainID.CELO: 'celo-mainnet',
    ChainID.LINEA: 'linea-mainnet',
    ChainID.POLYGON_ZKEVM: 'polygon-zkevm-mainnet',
}


class X402PaymentSigner:
    """Signs x402 payment payloads using EIP-712 / ERC-3009 transferWithAuthorization.

    The signer holds an ephemeral private key (generated once per process, never persisted).
    Fund `self.address` with USDC on Base to enable x402 GoldRush access.
    """

    def __init__(self, private_key: str) -> None:
        self._account: LocalAccount = EthAccount.from_key(private_key)

    @property
    def address(self) -> str:
        """Checksummed EVM address of the ephemeral payment wallet."""
        return self._account.address

    def sign_payment(self, payment_requirements: dict[str, Any]) -> str:
        """Build and return a base64-encoded X-PAYMENT header value.

        May raise:
        - KeyError if payment_requirements is missing required fields
        """
        pay_to: str = payment_requirements['payTo']
        amount: str = str(payment_requirements['maxAmountRequired'])
        network: str = payment_requirements.get('network', 'base-mainnet')
        asset: str = payment_requirements.get('asset', X402_USDC_CONTRACT)
        nonce_bytes: bytes = secrets.token_bytes(32)
        nonce_hex: str = '0x' + nonce_bytes.hex()
        valid_before: str = str(int(time.time()) + X402_PAYMENT_EXPIRY_SECONDS)

        domain_data: dict[str, Any] = {
            'name': X402_USDC_EIP712_NAME,
            'version': X402_USDC_EIP712_VERSION,
            'chainId': X402_BASE_CHAIN_ID,
            'verifyingContract': asset,
        }
        message_types: dict[str, list[dict[str, str]]] = {
            'TransferWithAuthorization': [
                {'name': 'from',        'type': 'address'},
                {'name': 'to',          'type': 'address'},
                {'name': 'value',       'type': 'uint256'},
                {'name': 'validAfter',  'type': 'uint256'},
                {'name': 'validBefore', 'type': 'uint256'},
                {'name': 'nonce',       'type': 'bytes32'},
            ],
        }
        message_data: dict[str, Any] = {
            'from':        self._account.address,
            'to':          pay_to,
            'value':       int(amount),
            'validAfter':  0,
            'validBefore': int(valid_before),
            'nonce':       nonce_bytes,
        }

        signed = EthAccount.sign_typed_data(
            private_key=self._account.key,
            domain_data=domain_data,
            message_types=message_types,
            message_data=message_data,
        )
        signature: str = signed.signature.hex()

        payload: dict[str, Any] = {
            'x402Version': X402_VERSION,
            'scheme': X402_SCHEME,
            'network': network,
            'payload': {
                'signature': signature,
                'authorization': {
                    'from':        self._account.address,
                    'to':          pay_to,
                    'value':       amount,
                    'validAfter':  '0',
                    'validBefore': valid_before,
                    'nonce':       nonce_hex,
                },
            },
        }
        return base64.b64encode(
            json.dumps(payload, separators=(',', ':')).encode(),
        ).decode()


class GoldRush(ExternalServiceWithApiKey, EtherscanLikeApi):
    """GoldRush (Covalent) API client. A single instance serves all EVM chains."""

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            signer: 'X402PaymentSigner | None' = None,
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
        self._signer: X402PaymentSigner | None = signer
        self._last_request_ts: float = 0.0
        # In-memory caches (Phase F)
        # ABI: (chain_id_value, address) → ABI object or None (None = no ABI found)
        self._abi_cache: dict[tuple[int, str], Any] = {}
        # block number: (chain_id_value, timestamp) → block number
        self._blocknum_cache: dict[tuple[int, int], int] = {}
        # activity: (chain_id_value, address) → (monotonic_ts, HasChainActivity) with 10-min TTL
        self._activity_cache: dict[tuple[int, str], tuple[float, HasChainActivity]] = {}

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

        if api_key is None and self._signer is None:
            raise RemoteError('GoldRush API key is not configured and no x402 wallet is set')

        url = f'{GOLDRUSH_BASE_URL}{path}'
        log.debug(f'Querying GoldRush: {url} params={params}')
        try:
            if api_key is not None:
                response = self.session.get(
                    url=url,
                    params=params or {},
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=(30, 30),
                )
            else:
                # x402 flow: probe then pay
                response = self.session.get(url=url, params=params or {}, timeout=(30, 30))
                if response.status_code == 402:
                    response = self._handle_x402(url=url, params=params, response=response)
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

    def _handle_x402(
            self,
            url: str,
            params: dict[str, Any] | None,
            response: 'requests.Response',
    ) -> 'requests.Response':
        """Sign a 402 payment requirement and retry the request with X-PAYMENT header.

        May raise:
        - RemoteError if the 402 body is unparseable, fields are missing, or the
          retry also fails (e.g. insufficient USDC balance). The error message
          includes self._signer.address so the user knows which wallet to fund.
        """
        assert self._signer is not None  # guaranteed by _request caller

        try:
            requirements: dict[str, Any] = response.json()
        except Exception as e:
            raise RemoteError(
                f'GoldRush x402: unparseable 402 body from {url}: {response.text}',
            ) from e

        try:
            x_payment = self._signer.sign_payment(requirements)
        except KeyError as e:
            raise RemoteError(
                f'GoldRush x402: missing field {e!s} in payment requirements from {url}',
            ) from e

        log.debug(
            f'GoldRush x402: payment signed for {url}, '
            f'wallet={self._signer.address}',
        )
        retry = self.session.get(
            url=url,
            params=params or {},
            headers={'X-PAYMENT': x_payment},
            timeout=(30, 30),
        )
        if retry.status_code == 402:
            raise RemoteError(
                f'GoldRush x402 payment rejected (insufficient USDC?). '
                f'Fund {self._signer.address} with USDC on Base '
                f'(chain 8453, contract {X402_USDC_CONTRACT}). '
                f'Response: {retry.text}',
            )
        return retry

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
        (`/transactions_v3/page/{page}/`) and uses `data.links.next` (not
        `data.pagination.has_more`) to signal whether a next page exists.

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

            # v3 uses links.next (not pagination.has_more) as the continuation signal
            if not (data.get('links') or {}).get('next'):
                break

            page_number += 1

        return all_items

    @staticmethod
    def _goldrush_tx_to_etherscan_fmt(item: dict[str, Any]) -> dict[str, Any]:
        """Convert a GoldRush transaction item to an Etherscan-compatible dict.

        May raise:
        - KeyError if required fields are missing
        """
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
        """Convert a Unix timestamp to a block number using GoldRush's block_v2 endpoint.

        May raise:
        - RemoteError if the API request fails or the response is malformed
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        slug = self._get_slug(chain_id)
        cache_key = (chain_id.value, int(ts))
        if cache_key in self._blocknum_cache:
            return self._blocknum_cache[cache_key]

        data = self._request(f'/{slug}/block_v2/{ts}/')
        items = (data.get('data') or {}).get('items') or []
        if not items or 'height' not in items[0]:
            raise RemoteError(
                f'GoldRush: could not resolve block for timestamp {ts} on {chain_id.name}',
            )
        block_number = int(items[0]['height'])
        self._blocknum_cache[cache_key] = block_number
        return block_number

    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> HasChainActivity:
        """Return whether the address has any on-chain activity.

        Uses GoldRush /{slug}/address/{addr}/ summary endpoint.
        Results are cached for 10 minutes.

        May raise:
        - RemoteError if the API request fails
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        cache_key = (chain_id.value, account)
        if cache_key in self._activity_cache:
            cached_ts, cached_result = self._activity_cache[cache_key]
            if time.monotonic() - cached_ts < 600:
                return cached_result

        slug = self._get_slug(chain_id)
        data = self._request(f'/{slug}/address/{account}/')
        summary = (data.get('data') or {}).get('items') or []
        item = summary[0] if summary else {}
        total_txns = item.get('total_transactions_count', 0) or 0
        if total_txns > 0:
            result = HasChainActivity.TRANSACTIONS
        elif len(item.get('token_balances') or []) > 0:
            result = HasChainActivity.TOKENS
        else:
            result = HasChainActivity.NONE

        self._activity_cache[cache_key] = (time.monotonic(), result)
        return result

    def get_contract_abi(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> Any | None:
        """Get the contract ABI for the given address if verified.

        Returns the parsed ABI object (list of dicts) or None if not found.
        Results are cached indefinitely (ABIs don't change).

        May raise:
        - RemoteError if the API request fails
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        cache_key = (chain_id.value, address)
        if cache_key in self._abi_cache:
            return self._abi_cache[cache_key]

        slug = self._get_slug(chain_id)
        data = self._request(f'/{slug}/contract/{address}/')
        items = (data.get('data') or {}).get('items') or []
        if not items or not items[0].get('contract_abi'):
            self._abi_cache[cache_key] = None
            return None

        abi = items[0]['contract_abi']
        self._abi_cache[cache_key] = abi
        return abi

    def get_contract_creation_hash(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> EVMTxHash | None:
        """Get the contract creation transaction hash for the given address.

        Returns None if the address is not a contract or has no creation data.

        May raise:
        - RemoteError if the API request fails
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        slug = self._get_slug(chain_id)
        data = self._request(f'/{slug}/contract/{address}/')
        items = (data.get('data') or {}).get('items') or []
        if not items:
            return None

        tx_hash_str: str = items[0].get('contract_deployment_transaction_hash', '') or ''
        if not tx_hash_str:
            return None

        try:
            return deserialize_evm_tx_hash(tx_hash_str)
        except DeserializationError as e:
            log.error(
                f'GoldRush: failed to deserialize creation hash for {address} '
                f'on {chain_id.name}: {e!s}',
            )
            return None

    @staticmethod
    def _goldrush_log_to_rotki_fmt(item: dict[str, Any]) -> dict[str, Any]:
        """Convert a GoldRush log/event item to an Etherscan-compatible dict format."""
        raw_topics = item.get('raw_log_topics') or []
        topics = [t.get('topic_hash', '') if isinstance(t, dict) else str(t) for t in raw_topics]
        return {
            'address': item.get('sender_address', ''),
            'data': item.get('raw_log_data', '0x') or '0x',
            'topics': topics,
            'blockNumber': item.get('block_height', 0),
            'transactionHash': item.get('tx_hash', ''),
            'logIndex': item.get('log_offset', 0),
        }

    def get_logs(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            contract_address: ChecksumEvmAddress,
            topics: list[str | None],
            from_block: int,
            to_block: int | str = 'latest',
            existing_events: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Get event logs for a contract address from GoldRush.

        May raise:
        - RemoteError if the API request fails
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        slug = self._get_slug(chain_id)
        params: dict[str, Any] = {
            'starting-block': str(from_block),
            'ending-block': str(to_block),
        }
        if topics and topics[0] is not None:
            params['topic0'] = topics[0]

        items = self._paginate(
            path=f'/{slug}/events/address/{contract_address}/',
            params=params,
        )
        return [self._goldrush_log_to_rotki_fmt(item) for item in items]

    def can_query_history(
            self,
            from_asset: Asset,
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: int | None = None,  # pylint: disable=unused-argument
    ) -> bool:
        """Return True if GoldRush can provide a historical price for this asset.

        GoldRush only supports EVM tokens with a known chain slug.
        """
        try:
            resolved = from_asset.resolve_to_asset_with_oracles()
        except Exception:  # noqa: BLE001
            return False

        if not resolved.is_evm_token():
            return False

        try:
            evm_token = resolved.resolve_to_evm_token()
            self._get_slug(evm_token.chain_id)
        except Exception:  # noqa: BLE001
            return False

        return True

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """Query the historical price of an EVM token via GoldRush pricing API.

        Uses /pricing/historical_by_addresses_v2/{slug}/{quote}/{address}/ endpoint.

        May raise:
        - PriceQueryUnsupportedAsset if the asset is not an EVM token on a supported chain
        - NoPriceForGivenTimestamp if GoldRush has no price data for this token/time
        - RemoteError if the API request fails
        """
        try:
            from_resolved = from_asset.resolve_to_asset_with_oracles()
        except Exception as e:
            raise PriceQueryUnsupportedAsset(from_asset.identifier) from e

        if not from_resolved.is_evm_token():
            raise PriceQueryUnsupportedAsset(from_asset.identifier)

        evm_token = from_resolved.resolve_to_evm_token()
        try:
            slug = self._get_slug(evm_token.chain_id)
        except ChainNotSupported as e:
            raise PriceQueryUnsupportedAsset(from_asset.identifier) from e

        contract_address = evm_token.evm_address
        date_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d')
        data = self._request(
            f'/pricing/historical_by_addresses_v2/{slug}/USD/{contract_address}/',
            params={'from': date_str, 'to': date_str},
        )
        items = data.get('data') or []
        if not items:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )

        prices = items[0].get('prices') or []
        if not prices or not prices[0].get('price'):
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )

        usd_price = Price(FVal(prices[0]['price']))
        if to_asset.identifier == A_USD.identifier:
            return usd_price

        from rotkehlchen.inquirer import Inquirer
        rate = Inquirer.find_price(from_asset=A_USD, to_asset=to_asset)
        return Price(usd_price * rate)

    def get_nfts(
            self,
            account: ChecksumEvmAddress,
            chain_id: ChainID = ChainID.ETHEREUM,
    ) -> list[dict[str, Any]]:
        """Get NFTs owned by account from GoldRush.

        Uses /{slug}/address/{account}/balances_nft/ endpoint (current; nfts_v2 is legacy).
        Returns a list of raw GoldRush NFT collection items; each item contains a
        `nft_data` array with the individual token entries.

        Response structure per item:
          contract_address, contract_name, nft_data[{token_id, token_url,
          external_data: {name, image, image_256, image_512, image_1024}}]

        May raise:
        - RemoteError if the API request fails
        - ChainNotSupported if the chain is not in CHAINID_TO_GOLDRUSH_SLUG
        """
        slug = self._get_slug(chain_id)
        return self._paginate(
            path=f'/{slug}/address/{account}/balances_nft/',
            params={'no-spam': 'true'},
        )

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """Not supported by GoldRush — raises RemoteError so _try_indexers tries next indexer."""
        raise RemoteError('GoldRush does not support L1 fee queries')

