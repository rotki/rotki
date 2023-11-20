import logging
import sys
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, Optional
from urllib.parse import urlencode

import gevent
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    WITHDRAWALS_IDX_PREFIX,
    WITHDRAWALS_TS_PREFIX,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import ChecksumEvmAddress, ExternalService, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, iso8601ts_to_timestamp, set_user_agent, ts_sec_to_ms
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Blockscout(ExternalServiceWithApiKey):
    """Blockscout API handler https://eth.blockscout.com/api-docs"""

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.BLOCKSCOUT)
        self.db: DBHandler  # specifying DB is not optional
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        set_user_agent(self.session)
        self.url = 'https://eth.blockscout.com/api/v2/'

    def _query(
            self,
            module: Literal['addresses'],
            endpoint: Literal['withdrawals'],
            encoded_args: str,
            extra_args: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Query blockscout

        May raise:
        - RemoteError due to problems querying blockscout
        """
        extra_args = {} if extra_args is None else extra_args
        query_str = f'{self.url}{module}/{encoded_args}/{endpoint}'
        api_key = self._get_api_key()
        if api_key is not None:
            extra_args['apikey'] = api_key

        if extra_args:
            query_str += f'?{urlencode(extra_args)}'

        log.debug(f'Querying blockscout API for {query_str}')
        times = CachedSettings().get_query_retry_limit()
        retries_num = times
        timeout = CachedSettings().get_timeout_tuple()
        backoff_in_seconds = 10

        while True:
            try:
                response = self.session.get(query_str, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Querying {query_str} failed due to {e!s}') from e

            if response.status_code == 429:
                if times == 0:
                    msg = (
                        f'Blockscout API request {response.url} failed '
                        f'with HTTP status code {response.status_code} and text '
                        f'{response.text} after {retries_num} retries'
                    )
                    log.debug(msg)
                    raise RemoteError(msg)

                # Rate limited. Try incremental backoff
                sleep_seconds = backoff_in_seconds * (retries_num - times + 1)
                times -= 1
                log.debug(
                    f'Blockscout API request {response.url} got rate limited. Sleeping for '
                    f'{sleep_seconds}. We have {times} tries left.',
                )
                gevent.sleep(sleep_seconds)
                continue

            if response.status_code != 200:
                raise RemoteError(
                    f'Blockscout API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            break  # all good got a response

        try:
            json_ret = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Blockscout API returned invalid JSON response: {response.text}',
            ) from e

        return json_ret

    def query_withdrawals(self, address: ChecksumEvmAddress) -> None:
        """Query withdrawals for an ethereum address and save them in the DB

        May raise:
        - RemoteError if blockscout query fails
        - DeserializationError if we can't decode the response
        - KeyError if the response from blockscout does not contain expected keys
        """
        extra_args: dict[str, Any] = {}
        range_name = f'{WITHDRAWALS_IDX_PREFIX}_{address}'
        ts_range_name = f'{WITHDRAWALS_TS_PREFIX}_{address}'
        dbevents = DBHistoryEvents(self.db)
        last_known_withdrawal_idx, index_to_write, ts_to_write = sys.maxsize, None, Timestamp(0)
        withdrawals: list[EthWithdrawalEvent] = []
        with self.db.conn.read_ctx() as cursor:
            if (idx_result := self.db.get_used_query_range(cursor, range_name)) is not None:
                last_known_withdrawal_idx = idx_result[1]

        while True:
            result = self._query(module='addresses', endpoint='withdrawals', encoded_args=address, extra_args=extra_args)  # noqa: E501
            if len(result['items']) == 0:
                log.debug(f'Could not find withdrawals for address {address}')
                break

            if index_to_write is None:
                index_to_write = result['items'][0]['index']
                ts_to_write = iso8601ts_to_timestamp(result['items'][0]['timestamp'])

            withdrawals = []
            for entry in result['items']:
                if entry['index'] >= last_known_withdrawal_idx:
                    break  # found a known one

                try:
                    withdrawals.append(EthWithdrawalEvent(
                        validator_index=int(entry['validator_index']),
                        timestamp=ts_sec_to_ms(iso8601ts_to_timestamp(entry['timestamp'])),
                        balance=Balance(amount=from_wei(deserialize_fval(
                            value=entry['amount'],
                            name='withdrawal amount',
                            location='blockscout staking withdrawals query',
                        ))),
                        withdrawal_address=address,
                        is_exit=False,  # TODO: needs to be figured out later, possibly in another task  # noqa: E501
                    ))
                except (ValueError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'missing key {msg}'

                    msg = f'Failed to deserialize an ETH withdrawal from blockscout due to {msg}'
                    log.error(f'{msg}. Entry: {entry}')
                    raise DeserializationError(msg) from e

            else:  # did not stop due to finding known index
                with self.db.user_write() as write_cursor:
                    dbevents.add_history_events(write_cursor, history=withdrawals)
                if (next_params := result['next_page_params']) is None:
                    break  # got no more pages

                extra_args = {'index': next_params['index'], 'items_count': next_params['items_count']}  # noqa: E501
                continue

            # if we get here it means we found a known index so we break out
            if len(withdrawals) != 0:
                with self.db.user_write() as write_cursor:
                    dbevents.add_history_events(write_cursor, history=withdrawals)
            break

        if index_to_write is not None:  # let's also update index if needed
            with self.db.user_write() as write_cursor:
                self.db.update_used_query_range(write_cursor, range_name, Timestamp(0), index_to_write)  # noqa: E501
                self.db.update_used_query_range(write_cursor, ts_range_name, Timestamp(0), ts_to_write)  # noqa: E501  # type: ignore
