import logging
import sys
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, overload

import gevent
import requests

from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi, HasChainActivity
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.externalapis.utils import get_earliest_ts, maybe_read_integer
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_int
from rotkehlchen.types import (
    BLOCKSCOUT_TO_CHAINID,
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, iso8601ts_to_timestamp, set_user_agent, ts_sec_to_ms
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

# Blockscout returns a maximum of 10000 transactions per request.
# https://docs.blockscout.com/devs/apis/rpc/account#get-transactions-by-address
BLOCKSCOUT_PAGINATION_LIMIT = 10000

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Blockscout(EtherscanLikeApi):
    """Blockscout API handler https://eth.blockscout.com/api-docs"""

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        EtherscanLikeApi.__init__(
            self,
            database=database,
            msg_aggregator=msg_aggregator,
            name='Blockscout',
            pagination_limit=BLOCKSCOUT_PAGINATION_LIMIT,
            default_api_key=ApiKey(''),  # no default api key used for blockscout
        )
        self.session = create_session()
        set_user_agent(self.session)
        self.service_details: dict[ChainID, ExternalServiceWithApiKey] = {
            chain_id: ExternalServiceWithApiKey(database=database, service_name=service_name)
            for service_name, chain_id in BLOCKSCOUT_TO_CHAINID.items()
        }

    @staticmethod
    def _get_url(chain_id: ChainID) -> str:
        match chain_id:
            case ChainID.ETHEREUM:
                return 'https://eth.blockscout.com/api'
            case ChainID.OPTIMISM:
                return 'https://explorer.optimism.io/api'
            case ChainID.BASE:
                return 'https://base.blockscout.com/api'
            case ChainID.ARBITRUM_ONE:
                return 'https://arbitrum.blockscout.com/api'
            case ChainID.GNOSIS:
                return 'https://gnosis.blockscout.com/api'
            case ChainID.POLYGON_POS:
                return 'https://polygon.blockscout.com/api'
            case ChainID.SCROLL:
                return 'https://scroll.blockscout.com/api'
            case _:
                raise ChainNotSupported(f'Blockscout does not support {chain_id.name}')

    def _get_api_key_for_chain(self, chain_id: ChainID) -> ApiKey | None:
        """Blockscout has different keys for each chain. Returns None if the requested
        chain is not present in the service_details dict.
        """
        if (service_for_chain := self.service_details.get(chain_id)) is None:
            return None

        return service_for_chain._get_api_key()

    @staticmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        """No-op for blockscout as the entire _query function is overridden."""
        return {}

    def _query_and_process(
            self,
            query_str: str,
            params: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
            http_method: Literal['get', 'post'] = 'get',
    ) -> dict[str, Any]:
        """Shared logic between v1 and v2 for querying blockscout api"""
        log.debug(f'Querying blockscout API for {query_str} with {params}')
        times = (cached_settings := CachedSettings()).get_query_retry_limit()
        retries_num = times
        timeout = timeout or cached_settings.get_timeout_tuple()
        backoff_in_seconds = 10

        while True:
            try:
                response = self.session.request(
                    method=http_method,
                    url=query_str,
                    timeout=timeout,
                    **{'params' if http_method == 'get' else 'json': params},  # type: ignore[arg-type]
                )
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

    @overload  # type: ignore[override]
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: Literal['account'],
            action: Literal['txlistinternal', 'txlist', 'tokentx'],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: Literal['account'],
            action: Literal['balance'],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> int:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: Literal['block'],
            action: Literal['getblocknobytime'],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any] | int:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: str,
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | str | int | dict[str, Any] | None:
        ...

    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: str,
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | str | int | dict[str, Any] | None:
        query_args = {} if options is None else options
        query_args |= {'module': module, 'action': action}
        if (api_key := self._get_api_key_for_chain(chain_id)) is not None:
            query_args['apikey'] = api_key
        response = self._query_and_process(
            query_str=self._get_url(chain_id=chain_id),
            params=query_args,
            timeout=timeout,
        )
        if str(response.get('status')) == '2':  # Missing data, fall back to other indexers
            raise RemoteError(f'Blockscout is missing data for {query_args}: {response}')

        if (
            (message := response.get('message')) is not None and
            message.startswith('No') and
            message.endswith('found')
        ):  # tokentx "No token transfers found", "No internal transactions found" and "No transactions found"  # noqa: E501
            return []
        elif message == 'Contract source code not verified':
            return None
        elif message != 'OK':
            raise RemoteError(f'Non ok response from blockscout v1 with {query_args}: {response}')

        if (result := response.get('result')) is None:
            raise RemoteError(f'Missing result from blockscout v1 response with {query_args}: {response}')  # noqa: E501

        if module == 'account':
            if action in ('txlistinternal', 'txlist', 'tokentx'):
                if not isinstance(result, list):
                    raise RemoteError(f'Expected a list result from blockscout v1 response with {query_args}: {response}')  # noqa: E501
            elif not isinstance(result, str):
                raise RemoteError(f'Expected a str result from blockscout v1 response with {query_args}: {response}')  # noqa: E501
            else:  # can only be 'str'` for balance
                try:
                    result = int(result)
                except ValueError as e:
                    raise RemoteError(f'Expected a stringified int result from blockscout v1 response with {query_args}: {response}') from e  # noqa: E501

        elif module == 'block' and not isinstance(result, (dict, int)):
            raise RemoteError(f'Expected a dict or int result from blockscout v1 response with {query_args}: {response}')  # noqa: E501

        return result

    @overload
    def _query_v2(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: Literal['addresses'],
            encoded_args: str,
            endpoint: Literal['withdrawals'],
            extra_args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    @overload
    def _query_v2(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: Literal['transactions'],
            encoded_args: str,
            endpoint: None = None,
            extra_args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def _query_v2(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: Literal['addresses', 'transactions'],
            encoded_args: str,
            endpoint: Literal['withdrawals'] | None = None,
            extra_args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query blockscout v2 endpoints

        May raise:
        - RemoteError due to problems querying blockscout
        """
        extra_args = {} if extra_args is None else extra_args
        query_str = f'{self._get_url(chain_id)}/v2/{module}/{encoded_args}'
        if endpoint is not None:
            query_str += f'/{endpoint}'
        if (api_key := self._get_api_key_for_chain(chain_id)) is not None:
            extra_args['apikey'] = api_key

        return self._query_and_process(
            query_str=query_str,
            params=extra_args,
        )

    @overload
    def _query_rpc_method(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            method: Literal[
                'eth_getBlockByNumber',
                'eth_getTransactionReceipt',
                'eth_getTransactionByHash',
            ],
            options: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    @overload
    def _query_rpc_method(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            method: Literal[
                'eth_blockNumber',
                'eth_getCode',
                'eth_call',
            ],
            options: dict[str, Any] | None = None,
    ) -> str:
        ...

    def _query_rpc_method(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            method: str,
            options: dict[str, Any] | None = None,
    ) -> str | dict[str, Any]:
        """Query blockscout rpc endpoints. Blockscout uses a format very similar to actual RPCs
        instead of a proxy module like etherscan.
        May raise RemoteError if there is a problem querying blockscout or the response is invalid.
        """
        if options is None:
            params = []
        elif method == 'eth_getBlockByNumber':
            # for eth_getBlockByNumber etherscan uses a 'true'/'false' string value for the
            # `boolean` parameter (specifies whether to return full transactions), while
            # blockscout requires an actual boolean value.
            params = [options.get('tag', 'latest'), options.get('boolean', 'true') == 'true']
        elif method == 'eth_call':
            tag = options.pop('tag', 'latest')
            params = [options, tag]
        elif method == 'eth_getCode':
            # the tag is required for blockscout, so need to ensure it is present.
            params = [options.get('address'), options.get('tag', 'latest')]
        else:
            params = list(options.values())

        if 'result' not in (response := self._query_and_process(
            query_str=f'{self._get_url(chain_id=chain_id)}/eth-rpc',
            params={
                'id': 0,
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
            },
            http_method='post',
        )):
            raise RemoteError(f'Blockscout eth-rpc response contains no result: {response}')

        return response['result']

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
            result = self._query_v2(
                chain_id=ChainID.ETHEREUM,  # querying withdrawals is always on ethereum
                module='addresses',
                endpoint='withdrawals',
                encoded_args=address,
                extra_args=extra_args,
            )
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
            chain_id: SUPPORTED_CHAIN_IDS,
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
        if ts < get_earliest_ts(chain_id):
            return 0  # behave like etherscan for timestamps close to the genesis

        response = self._query(
            chain_id=chain_id,
            module='block',
            action='getblocknobytime',
            options={'timestamp': ts, 'closest': closest},
        )

        if isinstance(response, int):
            return response

        elif (blocknumber := response.get('blockNumber')) is None:
            raise RemoteError(
                f'Invalid block number response from blockscout for {ts}: {response}',
            )

        try:
            return deserialize_int(
                value=blocknumber,
                location='blockscout blocknumber query',
            )
        except DeserializationError as e:
            raise RemoteError(
                f'Failed to deserialize blocknumber from blockscout response {response}',
            ) from e

    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> HasChainActivity:
        """Queries native asset balance, transactions, internal_txs and tokentx for an address
        just to quickly determine if the account has had any activity in the chain.
        We make a distinction between transactions and ERC20 transfers since ERC20
        are often spammed. If there was no activity at all we return the enum value
        NONE.

        May raise: RemoteError
        """
        options = {'address': str(account), 'page': 1}
        result = self._query(chain_id=chain_id, module='account', action='txlist', options=options)
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS

        result = self._query(chain_id=chain_id, module='account', action='txlistinternal', options=options)  # noqa: E501
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS

        result = self._query(chain_id=chain_id, module='account', action='tokentx', options=options)  # noqa: E501
        if len(result) != 0:
            return HasChainActivity.TOKENS

        if chain_id in {ChainID.ETHEREUM, ChainID.GNOSIS, ChainID.POLYGON_POS}:
            # since ethereum, gnosis and polygon have a lot of spam transactions for addresses
            # that were never used we add as requirement that in those chains the user must have
            # some balance.
            balance = self._query(
                chain_id=chain_id,
                module='account',
                action='balance',
                options={'address': account},
            )
            if balance != 0:
                return HasChainActivity.BALANCE

        return HasChainActivity.NONE

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """Query the L1 fee for the given tx hash from the v2 transactions endpoint.
        May raise:
        - RemoteError if unable to get the L1 fee amount or query fails.
        """
        response = self._query_v2(
            chain_id=chain_id,
            module='transactions',
            encoded_args=str(tx_hash),
        )
        try:
            return maybe_read_integer(data=response, key='l1_fee', api=self.name)
        except DeserializationError as e:
            raise RemoteError(f'Failed to get L1 fee from {self.name} due to {e!s}') from e
