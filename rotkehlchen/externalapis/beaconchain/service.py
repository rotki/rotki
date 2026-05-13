import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests
from gevent.lock import Semaphore

from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    BEACONCHAIN_MAX_EPOCH,
    DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE,
)
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorID
from rotkehlchen.chain.ethereum.modules.eth2.utils import calculate_query_chunks
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import APIKeyNotAvailable, RemoteError
from rotkehlchen.externalapis.interface import (
    ExternalServiceWithApiKey,
    ExternalServiceWithRecommendedApiKey,
)
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_fval,
)
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Eth2PubKey,
    ExternalService,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    convert_to_int,
    from_gwei,
    from_wei,
    set_user_agent,
    timestamp_to_iso8601,
    ts_now,
    ts_sec_to_ms,
)
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

from .constants import BEACONCHAIN_READ_TIMEOUT, BEACONCHAIN_ROOT_URL, MAX_WAIT_SECS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
BeaconChainEndpoint = Literal['block', 'block/rewards', 'validators', 'validators/proposal-slots']
BeaconChainValidatorEndpoint = Literal['validators', 'validators/proposal-slots']
BEACONCHAIN_VALIDATOR_LIMIT_RE: Final = re.compile(r'validator identifiers exceeds allowed limit')
BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE: Final = 20
BEACONCHAIN_VALIDATOR_LIMIT_CACHE_TTL: Final = 30 * DAY_IN_SECONDS


@dataclass(frozen=True)
class BeaconChainQueryResponse:
    data: list[dict[str, Any]] | dict[str, Any]
    next_cursor: str | None


class BeaconChain(ExternalServiceWithRecommendedApiKey):
    """BeaconChain handler https://docs.beaconcha.in/api/overview"""

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.BEACONCHAIN)
        self.msg_aggregator = msg_aggregator
        self.session = create_session()
        set_user_agent(self.session)
        self.url = f'{BEACONCHAIN_ROOT_URL}/api/v2/ethereum/'
        self.produced_blocks_lock = Semaphore()
        self.ratelimited_until = Timestamp(0)
        self.validator_query_chunk_size: int = self._get_cached_validator_query_limit()

    def _query_with_paging(
            self,
            endpoint: BeaconChainEndpoint,
            data: dict[str, Any] | None = None,
    ) -> BeaconChainQueryResponse:
        """
        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        if self.is_rate_limited():
            log.error(
                f'Beaconcha.in is rate limited until {self.ratelimited_until} when processing '
                f'{endpoint=} with {data=}',
            )
            raise RemoteError(
                'Beaconcha.in is rate limited until '
                f'{timestamp_to_iso8601(self.ratelimited_until)}. Check logs for more details',
            )

        query_str = f'{self.url}{endpoint}'

        if (api_key := self._get_api_key()) is None:
            log.warning('Missing beaconcha.in api key.')
            raise APIKeyNotAvailable(f'Querying {query_str} failed due to missing API key')

        if data is None:
            data = {}
        data['chain'] = 'mainnet'

        times = CachedSettings().get_query_retry_limit()
        retries_num = times
        timeout = (CachedSettings().get_timeout_tuple()[0], BEACONCHAIN_READ_TIMEOUT)
        backoff_in_seconds = 10
        log.debug(f'Querying beaconcha.in API for {query_str} with {data=}')
        while True:
            try:
                response = self.session.request(
                    method='POST',
                    url=query_str,
                    json=data,
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Querying {query_str} failed due to {e!s}') from e

            if response.status_code == 429:
                if (retry_after := response.headers.get('ratelimit-reset')) == '0':
                    self.db.delete_external_service_credentials([ExternalService.BEACONCHAIN])
                    self.api_key = None
                    self.last_ts = Timestamp(0)
                    raise APIKeyNotAvailable('Beaconcha.in free trial expired')

                rate_limit_info = (
                    f"limit: {response.headers.get('ratelimit-limit', 'unknown')}, "
                    f"remaining: {response.headers.get('ratelimit-remaining', 'unknown')}, "
                    f"window: {response.headers.get('ratelimit-window', 'unknown')}, "
                    f"bucket: {response.headers.get('ratelimit-bucket', 'unknown')}"
                )
                if times == 0:
                    msg = (
                        f'Beaconchain API request {response.url} failed '
                        f'with HTTP status code {response.status_code} and text '
                        f'{response.text} after {retries_num} retries. Rate limit info: '
                        f'{rate_limit_info}'
                    )
                    log.debug(msg)
                    raise RemoteError(msg)

                retry_after = retry_after or response.headers.get('retry-after')
                if retry_after is not None:
                    retry_after_secs = int(retry_after)
                    if retry_after_secs > MAX_WAIT_SECS:
                        msg = (
                            f'Beaconcha.in is rate limited when processing API request '
                            f'{response.url}. Would need to wait for {retry_after} seconds '
                            f'which is more than the wait limit of {MAX_WAIT_SECS} seconds. '
                            f'Bailing out. Rate limit info: {rate_limit_info}'
                        )
                        log.debug(msg)
                        self.ratelimited_until = Timestamp(ts_now() + retry_after_secs)
                        raise RemoteError(msg)
                    # else
                    sleep_seconds = retry_after_secs
                else:
                    # Rate limited. Try incremental backoff since ratelimit-reset header is missing
                    sleep_seconds = backoff_in_seconds * (retries_num - times + 1)
                times -= 1
                log.debug(
                    f'Beaconcha.in is rate limited for API request {response.url}. Sleeping '
                    f'for {sleep_seconds}. We have {times} tries left. Rate limit info: '
                    f'{rate_limit_info}',
                )
                gevent.sleep(sleep_seconds)
                continue
            # else
            break

        if response.status_code != 200:
            if response.status_code == 403:
                log.debug(
                    f'Beaconcha.in API returned HTTP 403 for {endpoint=}. '
                    f'This may indicate a validator query limit error. '
                    f'Response text: {response.text}',
                )
            raise RemoteError(
                f'Beaconchain API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Beaconchain API returned invalid JSON response: {response.text}',
            ) from e

        if 'data' not in json_ret:
            raise RemoteError(f'Beaconchain API did not contain a data key. Response: {json_ret}')

        paging = json_ret.get('paging', {})
        return BeaconChainQueryResponse(
            data=json_ret['data'],
            next_cursor=paging.get('next_cursor') or None if isinstance(paging, dict) else None,
        )

    def is_rate_limited(self) -> bool:
        return self.ratelimited_until > ts_now()

    def _get_cached_validator_query_limit(self) -> int:
        """Read cached beaconcha.in validator query limit for the current API key."""
        api_key = ExternalServiceWithApiKey._get_api_key(self)
        if api_key is None:
            return DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE

        with self.db.conn.read_ctx() as cursor:
            cache = self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.BEACONCHAIN_VALIDATOR_QUERY_LIMIT,
            )
        if not isinstance(cache, str):
            return DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE

        try:
            data = jsonloads_dict(cache)
            limit = int(data['limit'])
            timestamp = Timestamp(int(data['timestamp']))
        except (KeyError, TypeError, ValueError, JSONDecodeError) as e:
            log.warning(f'Ignoring invalid beaconcha.in validator limit cache: {cache}. {e!s}')
            return DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE

        if (
                data.get('api_key') != api_key or
                ts_now() - timestamp > BEACONCHAIN_VALIDATOR_LIMIT_CACHE_TTL or
                limit <= 0
        ):
            return DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE

        return min(limit, DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE)

    def _maybe_update_validator_query_limit(self, error: RemoteError) -> bool:
        """Detect and cache validator query limit for the current API key from errors."""
        if (
            BEACONCHAIN_VALIDATOR_LIMIT_RE.search(str(error)) is None or
            self.validator_query_chunk_size <= BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE
        ):
            return False

        log.debug(
            f'Detected beaconcha.in validator query limit error. '
            f'Adjusting chunk size from {self.validator_query_chunk_size} '
            f'to {BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE}. Error: {error!s}',
        )
        self.validator_query_chunk_size = BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE
        if (api_key := self._get_api_key()) is not None:
            with self.db.user_write() as write_cursor:
                self.db.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.BEACONCHAIN_VALIDATOR_QUERY_LIMIT,
                    value=json.dumps({
                        'api_key': api_key,
                        'limit': BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE,
                        'timestamp': ts_now(),
                    }),
                )
        return True

    def _query_chunked_endpoint_with_size(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
            endpoint: BeaconChainValidatorEndpoint,
            chunk_size: int,
    ) -> list[dict[str, Any]]:
        """Query a validator endpoint by splitting identifiers using the given chunk size.

        The chunk size is explicit so callers can first try the standard beaconcha.in limit and,
        after detecting a legacy/free-tier key, retry once with the known free-tier size.
        """
        data: list[dict[str, Any]] = []
        for chunk in calculate_query_chunks(
            indices_or_pubkeys=indices_or_pubkeys,
            chunk_size=chunk_size,
        ):
            result = self._query_with_paging(
                endpoint=endpoint,
                data={'validator': {'validator_identifiers': list(chunk)}},
            ).data
            if isinstance(result, list):
                data.extend(result)
            else:
                data.append(result)

        return data

    def _query_chunked_endpoint(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
            endpoint: BeaconChainValidatorEndpoint,
    ) -> list[dict[str, Any]]:
        try:
            return self._query_chunked_endpoint_with_size(
                indices_or_pubkeys=indices_or_pubkeys,
                endpoint=endpoint,
                chunk_size=self.validator_query_chunk_size,
            )
        except RemoteError as e:  # handle possible chunk size errors returned by beaconchain
            if not self._maybe_update_validator_query_limit(e):
                raise

        log.debug(
            f'Retrying beaconcha.in {endpoint} query with adjusted chunk size '
            f'{BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE} for '
            f'{len(indices_or_pubkeys)} validators',
        )
        return self._query_chunked_endpoint_with_size(  # retry once with the adjusted free size
            indices_or_pubkeys=indices_or_pubkeys,
            endpoint=endpoint,
            chunk_size=BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE,
        )

    def _query_cursor_paginated_chunk(
            self,
            chunk: Sequence[int],
            endpoint: BeaconChainValidatorEndpoint,
            page_size: int,
    ) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            response = self._query_with_paging(
                endpoint=endpoint,
                data={
                    'validator': {'validator_identifiers': list(chunk)},
                    'cursor': cursor or '',
                    'page_size': page_size,
                },
            )
            result = response.data
            data.extend(result)  # type: ignore[arg-type]  # is a list here
            if not isinstance(result, list) or (cursor := response.next_cursor) in (None, ''):
                break

        return data

    def _query_chunked_endpoint_with_cursor_pagination_with_size(
            self,
            indices: list[int],
            endpoint: BeaconChainValidatorEndpoint,
            page_size: int,
            chunk_size: int,
    ) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for chunk in calculate_query_chunks(indices_or_pubkeys=indices, chunk_size=chunk_size):
            data.extend(self._query_cursor_paginated_chunk(
                chunk=chunk,  # type: ignore[arg-type]  # chunk has the same type as indices
                endpoint=endpoint,
                page_size=page_size,
            ))

        return data

    def _query_chunked_endpoint_with_cursor_pagination(
            self,
            indices: list[int],
            endpoint: BeaconChainValidatorEndpoint,
            page_size: int,
    ) -> list[dict[str, Any]]:
        """Queries chunked endpoints with cursor pagination in beaconchain."""
        try:
            return self._query_chunked_endpoint_with_cursor_pagination_with_size(
                indices=indices,
                endpoint=endpoint,
                page_size=page_size,
                chunk_size=self.validator_query_chunk_size,
            )
        except RemoteError as e:
            if not self._maybe_update_validator_query_limit(e):
                raise

        log.debug(
            f'Retrying beaconcha.in {endpoint} cursor-paginated query with adjusted '
            f'chunk size {BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE} for '
            f'{len(indices)} validators',
        )
        return self._query_chunked_endpoint_with_cursor_pagination_with_size(
            indices=indices,
            endpoint=endpoint,
            page_size=page_size,
            chunk_size=BEACONCHAIN_FREE_VALIDATOR_CHUNK_SIZE,
        )

    @staticmethod
    def _normalize_validator_entry(entry: dict[str, Any]) -> dict[str, Any]:
        """Convert beaconcha.in V2 validator shape to the V1-like shape used internally."""
        validator = entry['validator']
        life_cycle_epochs = entry.get('life_cycle_epochs', {})
        balances = entry.get('balances', {})
        withdrawal_credentials = entry.get('withdrawal_credentials', {})
        withdrawal_credential = withdrawal_credentials.get('credential', '')
        if (
                (prefix := withdrawal_credentials.get('prefix')) is not None and
                not withdrawal_credential.startswith(prefix)
        ):
            withdrawal_credential = f'{prefix}{withdrawal_credential.removeprefix("0x")}'

        return {
            'activationeligibilityepoch': life_cycle_epochs.get('activation_eligibility', 0),
            'activationepoch': life_cycle_epochs.get('activation', 0),
            'balance': convert_to_int(from_wei(deserialize_fval(
                balances.get('current', 0),
                'balance',
                'beaconcha.in validator',
            )) / from_gwei(1)),
            'effectivebalance': convert_to_int(from_wei(deserialize_fval(
                balances.get('effective', 0),
                'effective balance',
                'beaconcha.in validator',
            )) / from_gwei(1)),
            'exitepoch': life_cycle_epochs.get('exit') or BEACONCHAIN_MAX_EPOCH,
            'lastattestationslot': 0,
            'name': '',
            'pubkey': validator['public_key'],
            'slashed': entry.get('slashed', False),
            'status': entry.get('status', ''),
            'validatorindex': validator['index'],
            'withdrawableepoch': life_cycle_epochs.get('withdrawable') or BEACONCHAIN_MAX_EPOCH,
            'withdrawalcredentials': withdrawal_credential,
            'total_withdrawals': 0,
        }

    def _query_block_data(self, block_number: int) -> dict[str, Any]:
        return self._query_with_paging(
            endpoint='block',
            data={'block': {'number': block_number}},
        ).data  # type: ignore[return-value]  # endpoint returns an object

    def _query_block_rewards(self, block_number: int) -> dict[str, Any]:
        return self._query_with_paging(
            endpoint='block/rewards',
            data={'block': {'number': block_number}},
        ).data  # type: ignore[return-value]  # endpoint returns an object

    def get_validator_data(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
    ) -> list[dict[str, Any]]:
        """Returns data for the given validators

        Essentially calls:
        https://docs.beaconcha.in/api-reference/ethereum/validators

        May raise:
        - RemoteError if there is problems querying Beaconcha.in
        """
        return [
            self._normalize_validator_entry(entry)
            for entry in self._query_chunked_endpoint(
                indices_or_pubkeys=indices_or_pubkeys,
                endpoint='validators',
            )
        ]

    def _get_validators_to_query_for_blocks(
            self,
            where: str,
            bindings: tuple[int] | None = None,
    ) -> list[int]:
        """Get a list of indices for validators that need to be queried for produced blocks.
        Args:
            `where`: SQL where clause to filter the validators
            `bindings`: Query bindings needed by the where clause
        """
        with self.db.conn.read_ctx() as cursor:
            key_name = DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS.value[0][:30]
            cursor.execute(
                'SELECT ev.validator_index FROM eth2_validators ev '
                f"LEFT JOIN key_value_cache kv ON kv.name = '{key_name}' || ev.validator_index "
                f'{where} ORDER BY ev.validator_index',
                bindings or (),
            )
            return [row[0] for row in cursor]

    def get_validators_to_query_for_blocks(self) -> list[int]:
        """Get indices of validators that are either active, exited but never queried,
        or exited and queried but exited timestamp is after last query timestamp.
        """
        return self._get_validators_to_query_for_blocks(
            where='WHERE kv.name IS NULL OR ev.exited_timestamp IS NULL OR ev.exited_timestamp > kv.value',  # noqa: E501
        )

    def get_outdated_validators_to_query_for_blocks(self) -> list[int]:
        """Get indices of validators that have not already been queried for blocks
        within the last day, and that are either active, exited but never queried,
        or exited and queried but exited timestamp is after last query timestamp.
        """
        return self._get_validators_to_query_for_blocks(
            where='WHERE kv.name IS NULL OR (kv.value <= ? AND (ev.exited_timestamp IS NULL OR ev.exited_timestamp > kv.value))',  # noqa: E501
            bindings=(ts_now() - DAY_IN_SECONDS,),
        )

    def get_and_store_produced_blocks(
            self,
            indices: list[int],
            update_cache: bool = True,
    ) -> None:
        with self.produced_blocks_lock:
            self._get_and_store_produced_blocks(indices=indices, update_cache=update_cache)

    def _get_and_store_produced_blocks(
            self,
            indices: list[int],
            update_cache: bool = True,
    ) -> None:
        """Get blocks produced by a set of validator indices/pubkeys and store the
        data in the DB.

        https://docs.beaconcha.in/api-reference/ethereum/validators/proposal-slots
        https://docs.beaconcha.in/api-reference/ethereum/block/rewards

        Queries in chunks of 100 due to api limitations
        Saves them in the DB if they are not already saved.

        - The fee_recipient is the address that receives the block reward.
        - The block reward is the actual block reward that goes to the fee recipient.
        - The producer_fee_recipient can be missing. This only exists if the block is
        produced via a relay and is the "reported" recipient of the mev reward by
        the relay. Reported is important here and relays can lie and also make mistakes.
        - The mev_reward can be ZERO and it's what goes to the producer_fee_recipient as reported
        by the relay. It can also be wrong due to misreporting by the relay. Beaconchain
        can also tell us there is relay data but that relay data just saying recipient
        is same as producer and same amount, meaning no extra MEV reward.

        If `update_cache` is True (default), updates LAST_PRODUCED_BLOCKS_QUERY_TS to now
        for each validator. Set to False when refetching historical data so that the
        normal periodic query schedule is not affected.

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        # This will query everything. It can be filtered by time, but we need all history here.
        data = self._query_chunked_endpoint_with_cursor_pagination(
            indices=indices,
            endpoint='validators/proposal-slots',
            page_size=10,
        )
        dbevents = DBHistoryEvents(self.db)
        with self.db.conn.read_ctx() as cursor:
            ethereum_tracked_accounts = self.db.get_blockchain_accounts(cursor).get(SupportedBlockchain.ETHEREUM)  # noqa: E501
        try:
            for entry in data:
                if entry.get('block') is None:
                    continue

                blocknumber = int(entry['block'])
                with self.db.conn.read_ctx() as cursor:
                    cursor.execute(
                        'SELECT COUNT(*) from eth_staking_events_info WHERE is_exit_or_blocknumber IS ?',  # noqa: E501
                        (blocknumber,),
                    )
                    if cursor.fetchone()[0] != 0:
                        continue

                block_data = self._query_block_data(blocknumber)
                rewards_data = self._query_block_rewards(blocknumber)
                timestamp = ts_sec_to_ms(block_data['timestamp'])
                priority_fees = rewards_data.get('priority_fees', {})
                priority_fees_recipient = (
                    priority_fees.get('recipient', {}) if isinstance(priority_fees, dict) else {}
                )
                mev_data = rewards_data.get('mev', {})
                mev_recipient = mev_data.get('recipient', {}) if isinstance(mev_data, dict) else {}
                block_reward = from_wei(deserialize_fval(
                    priority_fees.get(
                        'amount',
                        rewards_data.get('execution_layer_reward', rewards_data.get('total', 0)),
                    ) if isinstance(priority_fees, dict) else rewards_data.get(
                        'execution_layer_reward',
                        rewards_data.get('total', 0),
                    ),
                    'block_reward',
                    'beaconcha.in produced blocks',
                ))
                mev_reward = from_wei(deserialize_fval(
                    mev_data.get(
                        'amount',
                        rewards_data.get('mev_reward', rewards_data.get('relay_reward', 0)),
                    ) if isinstance(mev_data, dict) else rewards_data.get(
                        'mev_reward',
                        rewards_data.get('relay_reward', 0),
                    ),
                    'mev_reward',
                    'beaconcha.in produced blocks',
                ))

                if (fee_recipient_raw := block_data.get(
                    'fee_recipient',
                    rewards_data.get('fee_recipient', priority_fees_recipient.get('address')),
                )) is None:
                    raise RemoteError(
                        'Beaconcha.in produced blocks response error. Missing fee recipient',
                    )
                fee_recipient = deserialize_evm_address(fee_recipient_raw)
                proposer_index = entry['validator']['index']

                block_event = EthBlockEvent(
                    validator_index=proposer_index,
                    timestamp=timestamp,
                    amount=block_reward,
                    fee_recipient=fee_recipient,
                    fee_recipient_tracked=fee_recipient in ethereum_tracked_accounts,
                    block_number=blocknumber,
                    is_mev_reward=False,
                )
                mev_event = None
                producer_fee_recipient = None

                if (relay := rewards_data.get('relay')) is not None:
                    producer_fee_recipient = deserialize_evm_address(
                        relay['producer_fee_recipient'],
                    )
                elif (mev_recipient_raw := mev_recipient.get('address')) is not None:
                    producer_fee_recipient = deserialize_evm_address(mev_recipient_raw)

                if producer_fee_recipient is not None and not (producer_fee_recipient == fee_recipient and mev_reward == block_reward):  # beaconchain can report mev + relay even if just relayer is used but no extra tx is made # noqa: E501
                    mev_event = EthBlockEvent(
                        validator_index=proposer_index,
                        timestamp=timestamp,
                        amount=mev_reward,
                        fee_recipient=producer_fee_recipient,
                        fee_recipient_tracked=producer_fee_recipient in ethereum_tracked_accounts,
                        block_number=blocknumber,
                        is_mev_reward=True,
                    )
                with self.db.user_write() as write_cursor:
                    dbevents.add_history_event(write_cursor=write_cursor, event=block_event)
                    if mev_event is not None:
                        dbevents.add_history_event(write_cursor=write_cursor, event=mev_event)

            if update_cache:
                with self.db.user_write() as write_cursor:
                    now = ts_now()
                    for index in indices:
                        self.db.set_dynamic_cache(
                            write_cursor=write_cursor,
                            name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
                            value=now,
                            index=index,
                        )

        except KeyError as e:  # raising and not continuing since if 1 key missing something is off
            raise RemoteError(
                f'Beaconcha.in produced blocks response error. Missing key entry {e!s}',
            ) from e

    def get_eth1_address_validators(self, address: ChecksumEvmAddress) -> list[ValidatorID]:
        """Get a list of Validators that are associated with the given eth1 address.

        Each entry is a tuple of (optional) validator index and pubkey.

        Index is not returned if the validator has not yet been seen by the Consensus layer

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        result = self._query_with_paging(
            endpoint='validators',
            data={'validator': {'deposit_address': address}},
        ).data
        if isinstance(result, list):
            data = result
        else:
            data = [result]

        try:
            validators = [
                ValidatorID(
                    index=x['validator']['index'],
                    public_key=x['validator']['public_key'],
                ) for x in data
            ]
        except KeyError as e:
            raise RemoteError(
                f'Beaconcha.in eth1 response processing error. Missing key entry {e!s}',
            ) from e
        return validators
