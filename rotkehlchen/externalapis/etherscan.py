import logging
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple

import gevent
from requests import Response
from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi
from rotkehlchen.externalapis.interface import ExternalServiceWithRecommendedApiKey
from rotkehlchen.externalapis.utils import maybe_read_integer
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    ExternalService,
    Timestamp,
)
from rotkehlchen.utils.misc import from_gwei, ts_sec_to_ms
from rotkehlchen.utils.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ETHERSCAN_PAGINATION_LIMIT: Final = 10000
ETHERSCAN_BASE_URL: Final = 'https://api.etherscan.io/v2/api'
ROTKI_PACKAGED_KEY: Final = ApiKey('W9CEV6QB9NIPUEHD6KNEYM4PDX6KBPRVVR')
# Etherscan v2 free tier is 3 req/s on a single API key shared across all
# chains. Keep the default at the documented free-tier rate; higher tiers can
# still proceed, and 429 responses will shrink dynamically if needed.
FREE_ETHERSCAN_RATE_LIMIT_RPS: Final = 3.0
FREE_ETHERSCAN_RATE_LIMIT_BURST: Final = 3


class EtherscanTier(NamedTuple):
    name: Literal['free_or_lite', 'standard', 'advanced', 'professional', 'pro_plus']
    rps: float
    burst: int


ETHERSCAN_TIER_BY_DAILY_LIMIT: Final[dict[int, EtherscanTier]] = {
    100000: EtherscanTier(
        name='free_or_lite',
        rps=FREE_ETHERSCAN_RATE_LIMIT_RPS,
        burst=FREE_ETHERSCAN_RATE_LIMIT_BURST,
    ),
    200000: EtherscanTier(name='standard', rps=10.0, burst=10),
    500000: EtherscanTier(name='advanced', rps=20.0, burst=20),
    1000000: EtherscanTier(name='professional', rps=30.0, burst=30),
    1500000: EtherscanTier(name='pro_plus', rps=30.0, burst=30),
}


class Etherscan(ExternalServiceWithRecommendedApiKey, EtherscanLikeApi):
    """Base class for all Etherscan implementations"""
    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        ExternalServiceWithRecommendedApiKey.__init__(
            self,
            database=database,
            service_name=ExternalService.ETHERSCAN,
        )
        EtherscanLikeApi.__init__(
            self,
            database=database,
            msg_aggregator=msg_aggregator,
            name='Etherscan',
            default_api_key=ROTKI_PACKAGED_KEY,
            pagination_limit=ETHERSCAN_PAGINATION_LIMIT,
            rate_limiter=TokenBucket(
                rps=FREE_ETHERSCAN_RATE_LIMIT_RPS,
                capacity=FREE_ETHERSCAN_RATE_LIMIT_BURST,
            ),
        )
        self.detect_api_key_tier()

    def _cache_api_key_tier(self, tier: EtherscanTier) -> None:
        with self.db.user_write() as write_cursor:
            self.db.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.ETHERSCAN_API_KEY_TIER,
                value=tier.name,
            )

    def _get_cached_api_key_tier(self) -> EtherscanTier | None:
        with self.db.conn.read_ctx() as cursor:
            if (cached_value := self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.ETHERSCAN_API_KEY_TIER,
            )) is None:
                return None

        for tier in ETHERSCAN_TIER_BY_DAILY_LIMIT.values():
            if tier.name == cached_value:
                return tier
        return None

    def _delete_cached_api_key_tier(self) -> None:
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name=?',
                (DBCacheStatic.ETHERSCAN_API_KEY_TIER.value,),
            )

    def _query_api_key_tier(self, api_key: ApiKey) -> EtherscanTier | None:
        try:
            result = self._query(
                chain_id=ChainID.ETHEREUM,
                module='getapilimit',
                action='getapilimit',
            )
        except RemoteError as e:
            log.debug(f'Failed to query Etherscan API key tier for {api_key} due to {e!s}')
            return None

        if not isinstance(result, dict) or not isinstance(
            credit_limit := result.get('creditLimit'),
            int,
        ):
            log.debug(f'Etherscan API key tier query returned unexpected result: {result}')
            return None

        if (tier := ETHERSCAN_TIER_BY_DAILY_LIMIT.get(credit_limit)) is None:
            log.debug(f'Etherscan API key has unknown daily credit limit: {credit_limit}')
            return None

        return tier

    def detect_api_key_tier(self) -> None:
        """Read/cache Etherscan's daily limit and adjust the token bucket.

        The getapilimit endpoint exposes only daily credits, not per-second limits. This means
        Free and Lite are indistinguishable (both 100k/day), so the 100k bucket stays at the
        documented Free tier of 3 rps.
        """
        if (api_key := self._get_api_key()) is None:
            self._rate_limiter.reset(
                rps=FREE_ETHERSCAN_RATE_LIMIT_RPS,
                capacity=FREE_ETHERSCAN_RATE_LIMIT_BURST,
            )
            return

        if (tier := self._get_cached_api_key_tier()) is None:
            if (tier := self._query_api_key_tier(api_key)) is None:
                return
            self._cache_api_key_tier(tier=tier)

        self._rate_limiter.reset(rps=tier.rps, capacity=tier.burst)
        log.debug(f'Detected Etherscan API key tier {tier.name}. Set rate limit to {tier.rps} rps')

    def on_api_key_changed(self) -> None:
        self.api_key = None
        self.last_ts = Timestamp(0)
        self._delete_cached_api_key_tier()
        super().on_api_key_changed()
        self.detect_api_key_tier()

    @staticmethod
    def _get_url(chain_id: ChainID) -> str:
        """Etherscan sends the chain in the params instead of having different urls."""
        return ETHERSCAN_BASE_URL

    def _get_api_key_for_chain(self, chain_id: ChainID) -> ApiKey | None:
        """Etherscan uses the same api key for all chains."""
        return self._get_api_key()

    @staticmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        return {
            'module': module,
            'action': action,
            'apikey': api_key,
            'chainid': str(chain_id.serialize()),
        }

    def _additional_json_response_handling(
            self,
            action: str,
            chain_id: ChainID,
            response: Response,
            json_ret: dict[str, Any],
            result: str,
            current_backoff: int,
    ) -> int | bool | list | None:
        """Handle etherscan specific error responses including rate limits, free tier limits, etc.
        Returns False if no special handling is needed, the integer backoff time for rate limits,
        or a list/None when that value is what needs to be returned from the query function.
        May raise RemoteError or ChainNotSupported if the result indicates an error.
        """
        if (status := int(json_ret.get('status', 1))) == 1:  # use .get since successful proxy calls do not include a status  # noqa: E501
            return False  # No special handling needed.
        elif status == 0:
            if result == 'Contract source code not verified':
                return None

            if json_ret.get('message', '') == 'NOTOK':
                if result.startswith((
                        'Max calls per sec rate',  # short-term rate limit (5 seconds)
                        'Max rate limit reached',  # different variant of the message above
                        'Free API access is temporarily unavailable',  # free tier apikey blocked during high load periods  # noqa: E501
                )):
                    log.debug(
                        f'Got response: {response.text} from {self.name} while '
                        f'querying chain {chain_id}. Will backoff for {current_backoff} seconds.',
                    )
                    self._rate_limiter.shrink_after_429()
                    gevent.sleep(current_backoff)
                    return current_backoff * 2

                elif result.startswith('Max daily'):
                    raise RemoteError(f'{self.name} max daily rate limit reached.')

                elif result.startswith('Free API access is not supported for this chain'):
                    raise ChainNotSupported(result)

        transaction_endpoint_and_none_found = (
                status == 0 and
                json_ret['message'] in {'No transactions found', 'No blocks found'} and
                action in {
                    'txlist',
                    'txlistinternal',
                    'tokentx',
                    'txsBeaconWithdrawal',
                    'getminedblocks',
                }
        )
        logs_endpoint_and_none_found = (
                status == 0 and
                json_ret['message'] == 'No records found' and
                'getLogs' in action
        )
        if transaction_endpoint_and_none_found or logs_endpoint_and_none_found:
            return []

        # else
        raise RemoteError(f'{chain_id} {self.name} returned error response: {json_ret}')

    def get_validated_blocks(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
    ) -> list[dict[str, Any]]:
        """Query etherscan for ethereum blocks validated by an address.

        This method is Ethereum only.

        May raise:
        - RemoteError if the query fails, the response is malformed, or pagination stops making
        progress.
        """
        options = self._process_timestamp_or_blockrange(
            chain_id=ChainID.ETHEREUM,
            period=period,
            options={'sort': 'asc', 'address': address, 'blocktype': 'blocks'},
        )
        blocks = []
        while True:
            previous_page_state = (options.get('startblock'), options.get('page'))
            result = self._query(
                chain_id=ChainID.ETHEREUM,
                module='account',
                action='getminedblocks',
                options=options,
            )
            if len(result) == 0:
                break

            blocks.extend(result)
            try:
                new_options = self._maybe_paginate(result=result, options=options)
            except KeyError as e:
                raise RemoteError(f'Malformed Etherscan validated blocks response for {address}: missing {e!s}') from e  # noqa: E501
            if new_options is None:
                break
            if (new_options.get('startblock'), new_options.get('page')) == previous_page_state:
                raise RemoteError(f'Etherscan validated blocks pagination made no progress for {address}')  # noqa: E501
            options = new_options

        return blocks

    def get_withdrawals(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
    ) -> set[int]:
        """Query etherscan for ethereum withdrawals of an address for a specific period
        and save them in the DB. Returns newly detected validators that were not tracked in the DB.

        This method is Ethereum only.

        May raise:
        - RemoteError if the etherscan query fails for some reason
        - DeserializationError if we can't decode the response properly
        """
        options = self._process_timestamp_or_blockrange(ChainID.ETHEREUM, period, {'sort': 'asc', 'address': address})  # noqa: E501
        last_withdrawal_idx = -1
        touched_indices = set()
        with self.db.conn.read_ctx() as cursor:
            if (idx_result := self.db.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.WITHDRAWALS_IDX,
                address=address,
            )) is not None:
                last_withdrawal_idx = idx_result
        dbevents = DBHistoryEvents(self.db)
        while True:
            result = self._query(
                chain_id=ChainID.ETHEREUM,
                module='account',
                action='txsBeaconWithdrawal',
                options=options,
            )
            if (result_length := len(result)) == 0:
                return set()

            withdrawals = []
            try:
                for entry in result:
                    validator_index = int(entry['validatorIndex'])
                    touched_indices.add(validator_index)
                    withdrawals.append(EthWithdrawalEvent(
                        validator_index=validator_index,
                        timestamp=ts_sec_to_ms(deserialize_timestamp(entry['timestamp'])),
                        amount=from_gwei(deserialize_fval(
                            value=entry['amount'],
                            name='withdrawal amount',
                            location='etherscan staking withdrawals query',
                        )),
                        withdrawal_address=address,
                        is_exit=False,  # is figured out later in a periodic task
                    ))

                last_withdrawal_idx = max(last_withdrawal_idx, int(result[-1]['withdrawalIndex']))

            except (KeyError, ValueError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'missing key {msg}'

                msg = f'Failed to deserialize {result_length} ETH withdrawals from etherscan due to {msg}'  # noqa: E501
                log.error(msg)
                raise DeserializationError(msg) from e

            try:
                with self.db.user_write() as write_cursor:
                    dbevents.add_history_events(write_cursor, history=withdrawals)
                    self.db.set_dynamic_cache(
                        write_cursor=write_cursor,
                        name=DBCacheDynamic.WITHDRAWALS_TS,
                        value=Timestamp(int(result[-1]['timestamp'])),
                        address=address,
                    )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                log.error(f'Could not write {result_length} withdrawals to {address} due to {e!s}')
                return set()

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        with self.db.conn.read_ctx() as cursor:
            cursor.execute('SELECT validator_index from eth2_validators WHERE validator_index IS NOT NULL')  # noqa: E501
            tracked_indices = {x[0] for x in cursor}

        if last_withdrawal_idx != - 1:  # let's also update index if needed
            with self.db.user_write() as write_cursor:
                self.db.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.WITHDRAWALS_IDX,
                    value=last_withdrawal_idx,
                    address=address,
                )

        return touched_indices - tracked_indices

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """Attempt to retrieve L1 fees from etherscan for the given tx via the txlist endpoint.
        May raise:
        - RemoteError if unable to get the L1 fee amount or query fails.
        """
        try:
            for raw_tx in self._query(
                chain_id=chain_id,
                module='account',
                action='txlist',
                options=self._process_timestamp_or_blockrange(
                    chain_id=chain_id,
                    period=TimestampOrBlockRange(
                        range_type='blocks',
                        from_value=block_number,
                        to_value=block_number,
                    ),
                    options={'address': str(account)},
                ),
            ):
                if raw_tx.get('hash') != str(tx_hash):
                    continue  # skip unrelated txs for this account in the same block

                return maybe_read_integer(data=raw_tx, key='L1FeesPaid', api=self.name)
        except (DeserializationError, RemoteError) as e:
            # If the query fails or L1FeesPaid is missing or invalid, log an error and return None.
            msg = str(e)
        else:
            msg = 'requested tx was not returned'

        raise RemoteError(
            f'Failed to retrieve L1 fees from {self.name} txlist for '
            f'{chain_id.to_name()} tx {tx_hash!s} due to {msg}',
        )
