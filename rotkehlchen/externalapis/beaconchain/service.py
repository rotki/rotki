import logging
from collections.abc import Sequence
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, cast
from urllib.parse import urlencode

import gevent
import requests
from gevent.lock import Semaphore

from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDailyStats, ValidatorID
from rotkehlchen.chain.ethereum.modules.eth2.utils import calculate_query_chunks
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_fval,
    deserialize_int,
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
    create_timestamp,
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


class BeaconChain(ExternalServiceWithApiKey):
    """BeaconChain handler https://beaconcha.in/api/v1/docs/"""

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.BEACONCHAIN)
        self.msg_aggregator = msg_aggregator
        self.session = create_session()
        self.warning_given = False
        set_user_agent(self.session)
        self.url = f'{BEACONCHAIN_ROOT_URL}/api/v1/'
        self.produced_blocks_lock = Semaphore()
        self.ratelimited_until = Timestamp(0)

    def is_rate_limited(self) -> bool:
        return self.ratelimited_until > ts_now()

    def _query(
            self,
            method: Literal['GET', 'POST'],
            module: Literal['validator', 'execution'],
            endpoint: Literal['performance', 'eth1', 'deposits', 'produced', 'stats'] | None,
            encoded_args: str = '',
            data: dict[str, Any] | None = None,
            extra_args: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """
        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        if self.is_rate_limited():
            log.error(
                f'Beaconcha.in is rate limited until {self.ratelimited_until} when processing '
                f'{module=} {endpoint=} {encoded_args=} with {data=}',
            )
            raise RemoteError(
                'Beaconcha.in is rate limited until '
                f'{timestamp_to_iso8601(self.ratelimited_until)}. Check logs for more details',
            )

        if endpoint is None:  # for now only validator data
            query_str = f'{self.url}{module}'
        elif endpoint in ('eth1', 'stats'):
            query_str = f'{self.url}{module}/{endpoint}/{encoded_args}'
        else:
            query_str = f'{self.url}{module}/{encoded_args}/{endpoint}'

        api_key = self._get_api_key()
        if api_key is not None:
            if extra_args is None:
                extra_args = {}
            extra_args['apikey'] = api_key

        if extra_args is not None:
            query_str += f'?{urlencode(extra_args)}'

        times = CachedSettings().get_query_retry_limit()
        retries_num = times
        timeout = (CachedSettings().get_timeout_tuple()[0], BEACONCHAIN_READ_TIMEOUT)
        backoff_in_seconds = 10
        log.debug(f'Querying beaconcha.in API for {query_str} with {data=}')
        while True:
            try:
                response = self.session.request(
                    method=method,
                    url=query_str,
                    json=data,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Querying {query_str} failed due to {e!s}') from e

            if response.status_code == 429:
                minute_rate_limit = response.headers.get('x-ratelimit-limit-minute', 'unknown')
                user_minute_rate_limit = response.headers.get('x-ratelimit-remaining-minute', 'unknown')  # noqa: E501
                daily_rate_limit = response.headers.get('x-ratelimit-limit-day', 'unknown')
                user_daily_rate_limit = response.headers.get('x-ratelimit-remaining-day', 'unknown')  # noqa: E501
                month_rate_limit = response.headers.get('x-ratelimit-limit-month', 'unknown')
                user_month_rate_limit = response.headers.get('x-ratelimit-remaining-month', 'unknown')  # noqa: E501
                if times == 0:
                    msg = (
                        f'Beaconchain API request {response.url} failed '
                        f'with HTTP status code {response.status_code} and text '
                        f'{response.text} after {retries_num} retries'
                    )
                    log.debug(
                        f'{msg} minute limit: {user_minute_rate_limit}/{minute_rate_limit}, '
                        f'daily limit: {user_daily_rate_limit}/{daily_rate_limit}, '
                        f'monthly limit: {user_month_rate_limit}/{month_rate_limit}',
                    )
                    raise RemoteError(msg)

                retry_after = response.headers.get('retry-after', None)
                if retry_after:
                    retry_after_secs = int(retry_after)
                    if retry_after_secs > MAX_WAIT_SECS:
                        msg = (
                            f'Beaconchain API request {response.url} got rate limited. Would '
                            f'need to wait for {retry_after} seconds which is more than the '
                            f'wait limit of {MAX_WAIT_SECS} seconds. Bailing out.'
                        )
                        log.debug(
                            f'{msg} minute limit: {user_minute_rate_limit}/{minute_rate_limit}, '
                            f'daily limit: {user_daily_rate_limit}/{daily_rate_limit}, '
                            f'monthly limit: {user_month_rate_limit}/{month_rate_limit}',
                        )
                        self.ratelimited_until = Timestamp(ts_now() + retry_after_secs)
                        raise RemoteError(msg)
                    # else
                    sleep_seconds = retry_after_secs
                else:
                    # Rate limited. Try incremental backoff since retry-after header is missing
                    sleep_seconds = backoff_in_seconds * (retries_num - times + 1)
                times -= 1
                log.debug(
                    f'Beaconchain API request {response.url} got rate limited. Sleeping '
                    f'for {sleep_seconds}. We have {times} tries left.'
                    f'minute limit: {user_minute_rate_limit}/{minute_rate_limit}, '
                    f'daily limit: {user_daily_rate_limit}/{daily_rate_limit}, '
                    f'monthly limit: {user_month_rate_limit}/{month_rate_limit}',
                )
                gevent.sleep(sleep_seconds)
                continue
            # else
            break

        if response.status_code != 200:
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

        if json_ret.get('status') != 'OK':
            raise RemoteError(f'Beaconchain API returned non-OK status. Response: {json_ret}')

        if 'data' not in json_ret:
            raise RemoteError(f'Beaconchain API did not contain a data key. Response: {json_ret}')

        return json_ret['data']

    def _query_chunked_endpoint(
            self,
            method: Literal['GET', 'POST'],
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
            module: Literal['validator'],
            endpoint: Literal['performance'] | None,
    ) -> list[dict[str, Any]]:
        chunks = calculate_query_chunks(indices_or_pubkeys)
        data: list[dict[str, Any]] = []
        for chunk in chunks:
            result = self._query(
                method=method,
                module=module,
                endpoint=endpoint,
                data={'indicesOrPubkey': ','.join(str(x) for x in chunk)},
            )
            if isinstance(result, list):
                data.extend(result)
            else:
                data.append(result)

        return data

    def _query_chunked_endpoint_with_pagination(
            self,
            indices: list[int],
            module: Literal['execution'],
            endpoint: Literal['produced'],
            limit: int,
    ) -> list[dict[str, Any]]:
        """Queries chunked endpoints with limit/offset in beaconchain

        Unfortunately max limit is not known. Default is 10. Tested with 50 and seems to work
        without too many delays.
        The offset unfortunately also starts from latest entry so no way to store
        anything to avoid extra calls at the moment.
        """
        chunks = calculate_query_chunks(
            indices_or_pubkeys=indices,
            chunk_size=80,  # reduce number of validators to 80 due to URL length
        )
        data: list[dict[str, Any]] = []
        for chunk in chunks:
            offset = 0
            while True:
                result = self._query(
                    method='GET',
                    module=module,
                    endpoint=endpoint,
                    encoded_args=','.join(str(x) for x in chunk),
                    extra_args={'offset': offset, 'limit': limit},
                )
                offset += limit
                data.extend(result)  # type: ignore[arg-type]  # is a list here
                if len(result) != limit:
                    break  # found the end for this chunk

        return data

    def get_validator_data(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
    ) -> list[dict[str, Any]]:
        """Returns data for the given validators

        Essentially calls:
        https://beaconcha.in/api/v1/docs/index.html#/Validator/post_api_v1_validator

        May raise:
        - RemoteError if there is problems querying Beaconcha.in
        """
        return self._query_chunked_endpoint(
            method='POST',
            indices_or_pubkeys=indices_or_pubkeys,
            module='validator',
            endpoint=None,
        )

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
    ) -> None:
        with self.produced_blocks_lock:
            self._get_and_store_produced_blocks(indices)

    def _get_and_store_produced_blocks(
            self,
            indices: list[int],
    ) -> None:
        """Get blocks produced by a set of validator indices/pubkeys and store the
        data in the DB.

        https://beaconcha.in/api/v1/docs/index.html#/Execution/get_api_v1_execution__addressIndexOrPubkey__produced

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

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        # This will query everything. It's not filterable by time
        data = self._query_chunked_endpoint_with_pagination(
            indices=indices,
            module='execution',
            endpoint='produced',
            limit=50,
        )
        dbevents = DBHistoryEvents(self.db)
        with self.db.conn.read_ctx() as cursor:
            ethereum_tracked_accounts = self.db.get_blockchain_accounts(cursor).get(SupportedBlockchain.ETHEREUM)  # noqa: E501
        try:
            for entry in data:
                blocknumber = int(entry['blockNumber'])
                with self.db.conn.read_ctx() as cursor:
                    cursor.execute(
                        'SELECT COUNT(*) from eth_staking_events_info WHERE is_exit_or_blocknumber IS ?',  # noqa: E501
                        (blocknumber,),
                    )
                    if cursor.fetchone()[0] != 0:
                        continue

                timestamp = ts_sec_to_ms(entry['timestamp'])
                block_reward = from_wei(deserialize_fval(entry['blockReward'], 'block_reward', 'beaconcha.in produced blocks'))  # noqa: E501
                mev_reward = from_wei(deserialize_fval(entry['blockMevReward'], 'mev_reward', 'beaconcha.in produced blocks'))  # noqa: E501

                fee_recipient = deserialize_evm_address(entry['feeRecipient'])
                proposer_index = entry['posConsensus']['proposerIndex']

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

                if entry.get('relay') is not None:
                    producer_fee_recipient = deserialize_evm_address(entry['relay']['producerFeeRecipient'])  # noqa: E501
                    if not (producer_fee_recipient == fee_recipient and mev_reward == block_reward):  # beaconchain can report mev + relay even if just relayer is used but no extra tx is made # noqa: E501
                        mev_event = EthBlockEvent(
                            validator_index=proposer_index,
                            timestamp=timestamp,
                            amount=mev_reward,
                            fee_recipient=producer_fee_recipient,
                            fee_recipient_tracked=producer_fee_recipient in ethereum_tracked_accounts,  # noqa: E501
                            block_number=blocknumber,
                            is_mev_reward=True,
                        )
                with self.db.user_write() as write_cursor:
                    dbevents.add_history_event(write_cursor=write_cursor, event=block_event)
                    if mev_event is not None:
                        dbevents.add_history_event(write_cursor=write_cursor, event=mev_event)

            with self.db.user_write() as write_cursor:
                now = ts_now()
                for index in indices:
                    self.db.set_dynamic_cache(
                        write_cursor=write_cursor,
                        name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
                        value=now,
                        index=index,
                    )

        except KeyError as e:  # raising and not continuing since if 1 key missing something is off  # noqa: E501
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
        result = self._query(
            method='GET',
            module='validator',
            endpoint='eth1',
            encoded_args=address,
        )
        if isinstance(result, list):
            data = result
        else:
            data = [result]

        try:
            validators = [
                ValidatorID(
                    index=x['validatorindex'],
                    public_key=x['publickey'],
                ) for x in data
            ]
        except KeyError as e:
            raise RemoteError(
                f'Beaconcha.in eth1 response processing error. Missing key entry {e!s}',
            ) from e
        return validators

    def query_validator_daily_stats(
            self,
            validator_index: int,
            last_known_timestamp: Timestamp,
            exit_ts: Timestamp | None,
    ) -> list[ValidatorDailyStats]:
        """
        May raise:
        - RemoteError if we can't query beaconcha.in or if the data is not in the expected format
        """
        if exit_ts is not None and last_known_timestamp > exit_ts:
            return []  # nothing new to add

        data = cast('list[dict[str, Any]]', self._query(
            method='GET',
            module='validator',
            endpoint='stats',
            encoded_args=str(validator_index),
        ))

        timestamp = Timestamp(0)
        stats: list[ValidatorDailyStats] = []
        for day_data in data:
            try:
                start_effective_balance = day_data['start_effective_balance']
                if start_effective_balance is None:
                    start_effective_balance = ZERO
                elif deserialize_int(start_effective_balance) == ZERO:
                    continue  # validator exited

                end_effective_balance = None
                if day_data['end_effective_balance'] is not None:
                    end_effective_balance = deserialize_int(day_data['end_effective_balance'])
                withdrawals_amount = deserialize_int(day_data['withdrawals_amount'])

                try:
                    timestamp = create_timestamp(
                        datestr=f"{day_data['day_start']}",
                        formatstr='%Y-%m-%dT%I:%M:%S%z',
                    )
                except ValueError as e:
                    raise RemoteError(
                        f'Failed to parse {day_data["day_start"]} to timestamp',
                    ) from e

                if timestamp <= last_known_timestamp:
                    return stats  # we are done

                end_balance = start_balance = 0
                if (raw_end_balance := day_data['end_balance']) is not None:
                    end_balance = deserialize_int(raw_end_balance)

                if (raw_start_balance := day_data['start_balance']) is not None:
                    start_balance = deserialize_int(raw_start_balance)

            except KeyError as e:
                log.error(f'Missing key {e} in daily stats for {validator_index=}. Skipping day')
                continue

            except DeserializationError as e:
                log.error(f'Failed to deserialize daily stats for {validator_index=} due to {e}. Skipping day')  # noqa: E501
                continue

            # end balance in the api is the actual balance of the validator at the end of the day,
            # start balance is the actual balance of the validator at the start of the day,
            # end_effective_balance and start_effective_balance are the effective balance
            # of the validator at the end and start of the day. To calculate the PnL for the day
            # we subtract end_balance - start_balance. If the validator exists its
            # end_effective_balance becomes 0 and so does its end_balance. We obtain the PnL
            # as withdrawals_amount - start_balance
            pnl_as_int = end_balance - start_balance if end_effective_balance != 0 else withdrawals_amount - start_balance  # noqa: E501
            stats.append(ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=timestamp,
                pnl=from_gwei(pnl_as_int),
            ))

        return stats
