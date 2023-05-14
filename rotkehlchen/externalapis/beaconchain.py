import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, Optional, Union
from urllib.parse import urlencode

import gevent
import requests
from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import EthBlockEvent
from rotkehlchen.chain.ethereum.modules.eth2.constants import LAST_PRODUCED_BLOCKS_QUERY_TS
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorID, ValidatorPerformance
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.timing import DEFAULT_CONNECT_TIMEOUT, QUERY_RETRY_TIMES
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_fval
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, ExternalService, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, get_chunks, set_user_agent, ts_now, ts_sec_to_ms
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


MAX_WAIT_SECS = 60
BEACONCHAIN_READ_TIMEOUT = 75
BEACONCHAIN_TIMEOUT_TUPLE = (DEFAULT_CONNECT_TIMEOUT, BEACONCHAIN_READ_TIMEOUT)
BEACONCHAIN_ROOT_URL = 'https://beaconcha.in'

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _calculate_query_chunks(
        indices_or_pubkeys: Union[list[int], list[Eth2PubKey]],
) -> Union[list[list[int]], list[list[Eth2PubKey]]]:
    """Create chunks of queries.

    Beaconcha.in allows up to 100 validator or public keys in one query for most calls.
    Also has a URI length limit of ~8190, so seems no more than 80 public keys can be per call.
    """
    if len(indices_or_pubkeys) == 0:
        return []  # type: ignore

    n = 100
    if isinstance(indices_or_pubkeys[0], str):
        n = 80
    return list(get_chunks(indices_or_pubkeys, n=n))  # type: ignore


class BeaconChain(ExternalServiceWithApiKey):
    """Even though the beaconchain allows for API keys we don't implement it yet.
    We do extend ExternalServiceWithApiKey though so that it becomes easier to add
    in the future.

    https://beaconcha.in/api/v1/docs/
    """

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.BEACONCHAIN)
        self.db: 'DBHandler'  # specifying DB is not optional
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.warning_given = False
        set_user_agent(self.session)
        self.url = f'{BEACONCHAIN_ROOT_URL}/api/v1/'
        self.produced_blocks_lock = Semaphore()

    def _query(
            self,
            module: Literal['validator', 'execution'],
            endpoint: Optional[Literal['performance', 'eth1', 'deposits', 'produced']],  # noqa: E501
            encoded_args: str,
            extra_args: Optional[dict[str, Any]] = None,
    ) -> Union[list[dict[str, Any]], dict[str, Any]]:
        """
        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        if endpoint is None:  # for now only validator data
            query_str = f'{self.url}{module}/{encoded_args}'
        elif endpoint == 'eth1':
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

        times = QUERY_RETRY_TIMES
        backoff_in_seconds = 10
        log.debug(f'Querying beaconcha.in API for {query_str}')
        while True:
            try:
                response = self.session.get(query_str, timeout=BEACONCHAIN_TIMEOUT_TUPLE)
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
                        f'{response.text} after 5 retries'
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
                        raise RemoteError(msg)
                    # else
                    sleep_seconds = retry_after_secs
                else:
                    # Rate limited. Try incremental backoff since retry-after header is missing
                    sleep_seconds = backoff_in_seconds * (QUERY_RETRY_TIMES - times + 1)
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
            indices_or_pubkeys: Union[list[int], list[Eth2PubKey]],
            module: Literal['validator'],
            endpoint: Optional[Literal['performance']],
    ) -> list[dict[str, Any]]:
        chunks = _calculate_query_chunks(indices_or_pubkeys)
        data: list[dict[str, Any]] = []
        for chunk in chunks:
            result = self._query(
                module=module,
                endpoint=endpoint,
                encoded_args=','.join(str(x) for x in chunk),
            )
            if isinstance(result, list):
                data.extend(result)
            else:
                data.append(result)

        return data

    def _query_chunked_endpoint_with_pagination(
            self,
            indices_or_pubkeys: Union[list[int], list[Eth2PubKey]],
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
        chunks = _calculate_query_chunks(indices_or_pubkeys)
        data: list[dict[str, Any]] = []
        for chunk in chunks:
            offset = 0
            while True:
                result = self._query(
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
            indices_or_pubkeys: Union[list[int], list[Eth2PubKey]],
    ) -> list[dict[str, Any]]:
        """Returns data for the given validators

        Essentially calls:
        https://beaconcha.in/api/v1/docs/index.html#/Validator/get_api_v1_validator__indexOrPubkey_
        """
        return self._query_chunked_endpoint(
            indices_or_pubkeys=indices_or_pubkeys,
            module='validator',
            endpoint=None,
        )

    def get_performance(
            self,
            indices_or_pubkeys: Union[list[int], list[Eth2PubKey]],
    ) -> dict[int, ValidatorPerformance]:
        """Get the performance of all the validators given from the list of indices or pubkeys

        Queries in chunks of 100 due to api limitations

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        data = self._query_chunked_endpoint(
            indices_or_pubkeys=indices_or_pubkeys,
            module='validator',
            endpoint='performance',
        )
        try:
            performance = {}
            for entry in data:
                index = entry['validatorindex']
                performance[index] = ValidatorPerformance(
                    balance=entry['balance'],
                    performance_1d=entry['performance1d'],
                    performance_1w=entry['performance7d'],
                    performance_1m=entry['performance31d'],
                    performance_1y=entry['performance365d'],
                    performance_total=entry['performancetotal'],
                )
        except KeyError as e:
            raise RemoteError(
                f'Beaconcha.in performance response processing error. Missing key entry {e!s}',
            ) from e

        return performance

    def get_and_store_produced_blocks(
            self,
            indices_or_pubkeys: Union[list[int], list[Eth2PubKey]],
    ) -> None:
        with self.produced_blocks_lock:
            return self._get_and_store_produced_blocks(indices_or_pubkeys)

    def _get_and_store_produced_blocks(
            self,
            indices_or_pubkeys: Union[list[int], list[Eth2PubKey]],
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
        by the relay. It can also be wrong due to misreporting by the relay.

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        # This will query everything. It's not filterable by time
        data = self._query_chunked_endpoint_with_pagination(
            indices_or_pubkeys=indices_or_pubkeys,
            module='execution',
            endpoint='produced',
            limit=50,
        )
        dbevents = DBHistoryEvents(self.db)

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
                    balance=Balance(amount=block_reward),
                    fee_recipient=fee_recipient,
                    block_number=blocknumber,
                    is_mev_reward=False,
                )
                mev_event = None
                producer_fee_recipient = None

                if entry.get('relay') is not None:
                    producer_fee_recipient = deserialize_evm_address(entry['relay']['producerFeeRecipient'])  # noqa: E501
                    mev_event = EthBlockEvent(
                        validator_index=proposer_index,
                        timestamp=timestamp,
                        balance=Balance(amount=mev_reward),
                        fee_recipient=producer_fee_recipient,
                        block_number=blocknumber,
                        is_mev_reward=True,
                    )
                with self.db.user_write() as write_cursor:
                    dbevents.add_history_event(write_cursor=write_cursor, event=block_event)
                    if mev_event is not None:
                        dbevents.add_history_event(write_cursor=write_cursor, event=mev_event)

            with self.db.user_write() as write_cursor:
                self.db.update_used_query_range(
                    write_cursor=write_cursor,
                    name=LAST_PRODUCED_BLOCKS_QUERY_TS,
                    start_ts=Timestamp(0),
                    end_ts=ts_now(),
                )

        except KeyError as e:  # raising and not continuing since if 1 key missing something is off  # noqa: E501
            raise RemoteError(
                f'Beaconcha.in produced blocks response error. Missing key entry {e!s}',
            ) from e

    def get_eth1_address_validators(self, address: ChecksumEvmAddress) -> list[ValidatorID]:
        """Get a list of Validators that are associated with the given eth1 address.

        Each entry is a tuple of (optional) validator index and pubkey

        May raise:
        - RemoteError due to problems querying beaconcha.in API
        """
        result = self._query(
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
                    ownership_proportion=ONE,
                ) for x in data
            ]
        except KeyError as e:
            raise RemoteError(
                f'Beaconcha.in eth1 response processing error. Missing key entry {e!s}',
            ) from e
        return validators
