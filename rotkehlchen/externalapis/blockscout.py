import logging
import sys
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, overload

import gevent
import requests

from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import HasChainActivity
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.externalapis.utils import get_earliest_ts
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_int
from rotkehlchen.types import (
    BLOCKSCOUT_TO_CHAINID,
    SUPPORTED_EVM_CHAINS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, iso8601ts_to_timestamp, set_user_agent, ts_sec_to_ms
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Blockscout(ExternalServiceWithApiKey):
    """Blockscout API handler https://eth.blockscout.com/api-docs"""

    def __init__(
            self,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.chain_id = blockchain.to_chain_id()
        super().__init__(
            database=database,
            service_name={v: k for k, v in BLOCKSCOUT_TO_CHAINID.items()}[self.chain_id],
        )
        self.msg_aggregator = msg_aggregator
        self.session = create_session()
        set_user_agent(self.session)
        match blockchain:
            case SupportedBlockchain.ETHEREUM:
                self.url = 'https://eth.blockscout.com/api'
            case SupportedBlockchain.OPTIMISM:
                self.url = 'https://optimism.blockscout.com/api'
            case SupportedBlockchain.BASE:
                self.url = 'https://base.blockscout.com/api'
            case SupportedBlockchain.ARBITRUM_ONE:
                self.url = 'https://arbitrum.blockscout.com/api'
            case SupportedBlockchain.GNOSIS:
                self.url = 'https://gnosis.blockscout.com/api'
            case SupportedBlockchain.POLYGON_POS:
                self.url = 'https://polygon.blockscout.com/api'
            case SupportedBlockchain.SCROLL:
                self.url = 'https://scroll.blockscout.com/api'
            case _:
                raise NotImplementedError(f'Blockscout not implement for {blockchain}')

    def _query_and_process(
            self,
            query_str: str,
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Shared logic between v1 and v2 for querying blockscout api"""
        log.debug(f'Querying blockscout API for {query_str} with {params}')
        times = (cached_settings := CachedSettings()).get_query_retry_limit()
        retries_num = times
        timeout = cached_settings.get_timeout_tuple()
        backoff_in_seconds = 10

        while True:
            try:
                response = self.session.get(query_str, timeout=timeout, params=params)
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

        return json_ret  # 'txlistinternal', 'txlist', 'tokentx

    @overload
    def _query_v1(
            self,
            module: Literal['account'],
            action: Literal['txlistinternal', 'txlist', 'tokentx'],
            query_args: dict[str, Any] | None = None,
    ) -> list[Any]:
        ...

    @overload
    def _query_v1(
            self,
            module: Literal['account'],
            action: Literal['balance'],
            query_args: dict[str, Any] | None = None,
    ) -> int:
        ...

    @overload
    def _query_v1(
            self,
            module: Literal['block'],
            action: Literal['getblocknobytime'],
            query_args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    @overload
    def _query_v1(
            self,
            module: str,
            action: str,
            query_args: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | int:
        ...

    def _query_v1(
            self,
            module: str,
            action: str,
            query_args: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | int:
        query_args = {} if query_args is None else query_args
        query_args |= {'module': module, 'action': action}
        if (api_key := self._get_api_key()) is not None:
            query_args['apikey'] = api_key
        response = self._query_and_process(
            query_str=self.url,
            params=query_args,
        )
        if (
            (message := response.get('message')) is not None and
            message.startswith('No') and
            message.endswith('found')
        ):  # tokentx "No token transfers found", "No internal transactions found" and "No transactions found"  # noqa: E501
            return []
        elif message != 'OK':
            raise RemoteError(f'Non ok response from blockscout v1 with {query_args}: {response}')

        return response['result']

    def _query_v2(
            self,
            module: Literal['addresses'],
            endpoint: Literal['withdrawals'],
            encoded_args: str,
            extra_args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query blockscout v2 endpoints

        May raise:
        - RemoteError due to problems querying blockscout
        """
        extra_args = {} if extra_args is None else extra_args
        query_str = f'{self.url}/v2/{module}/{encoded_args}/{endpoint}'
        if (api_key := self._get_api_key()) is not None:
            extra_args['apikey'] = api_key

        return self._query_and_process(
            query_str=query_str,
            params=extra_args,
        )

    def query_withdrawals(self, address: ChecksumEvmAddress) -> set[int]:
        """Query withdrawals for an ethereum address and save them in the DB.
        Returns newly detected validators that were not tracked in the DB.

        May raise:
        - RemoteError if blockscout query fails
        - DeserializationError if we can't decode the response
        - KeyError if the response from blockscout does not contain expected keys
        """
        extra_args: dict[str, Any] = {}
        dbevents = DBHistoryEvents(self.db)
        last_known_withdrawal_idx, index_to_write, ts_to_write = sys.maxsize, None, Timestamp(0)
        withdrawals: list[EthWithdrawalEvent] = []
        touched_indices = set()
        with self.db.conn.read_ctx() as cursor:
            if (idx_result := self.db.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.WITHDRAWALS_IDX,
                address=address,
            )) is not None:
                last_known_withdrawal_idx = idx_result

        while True:
            result = self._query_v2(module='addresses', endpoint='withdrawals', encoded_args=address, extra_args=extra_args)  # noqa: E501
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
                    validator_index = int(entry['validator_index'])
                    touched_indices.add(validator_index)
                    withdrawals.append(EthWithdrawalEvent(
                        validator_index=validator_index,
                        timestamp=ts_sec_to_ms(iso8601ts_to_timestamp(entry['timestamp'])),
                        amount=from_wei(deserialize_fval(
                            value=entry['amount'],
                            name='withdrawal amount',
                            location='blockscout staking withdrawals query',
                        )),
                        withdrawal_address=address,
                        is_exit=False,  # is figured out later in a periodic task
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

        with self.db.conn.read_ctx() as cursor:
            cursor.execute('SELECT validator_index from eth2_validators WHERE validator_index IS NOT NULL')  # noqa: E501
            tracked_indices = {x[0] for x in cursor}

        if index_to_write is not None:  # let's also update index if needed
            with self.db.user_write() as write_cursor:
                self.db.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.WITHDRAWALS_IDX,
                    value=index_to_write,
                    address=address,
                )
                self.db.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.WITHDRAWALS_TS,
                    value=ts_to_write,
                    address=address,
                )

        return touched_indices - tracked_indices

    def get_blocknumber_by_time(
            self,
            ts: Timestamp,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """
        Query blockscout for the block at the given timestamp. Interface is compatible
        with the etherscan call.
        May raise:
        - RemoteError: If it fails to call the remote server or response doesn't have the correct
        format
        """
        if ts < get_earliest_ts(self.chain_id):
            return 0  # behave like etherscan for timestamps close to the genesis

        response = self._query_v1(
            module='block',
            action='getblocknobytime',
            query_args={'timestamp': ts, 'closest': closest},
        )
        try:
            return deserialize_int(
                value=response.get('blockNumber'),
                location='blockscout blocknumber query',
            )
        except DeserializationError as e:
            raise RemoteError(
                f'Failed to deserialize blocknumber from blockscout response {response}',
            ) from e

    def has_activity(self, account: ChecksumEvmAddress) -> HasChainActivity:
        """Queries native asset balance, transactions, internal_txs and tokentx for an address
        just to quickly determine if the account has had any activity in the chain.
        We make a distinction between transactions and ERC20 transfers since ERC20
        are often spammed. If there was no activity at all we return the enum value
        NONE.

        May raise: RemoteError
        """
        options = {'address': str(account), 'page': 1}
        result = self._query_v1(module='account', action='txlist', query_args=options)
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS

        result = self._query_v1(module='account', action='txlistinternal', query_args=options)
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS

        result = self._query_v1(module='account', action='tokentx', query_args=options)
        if len(result) != 0:
            return HasChainActivity.TOKENS

        if self.chain_id in {ChainID.ETHEREUM, ChainID.GNOSIS, ChainID.POLYGON_POS}:
            # since ethereum, gnosis and polygon have a lot of spam transactions for addresses
            # that were never used we add as requirement that in those chains the user must have
            # some balance.
            balance = self._query_v1(
                module='account',
                action='balance',
                query_args={'address': account},
            )
            if int(balance) != 0:
                return HasChainActivity.BALANCE

        return HasChainActivity.NONE
