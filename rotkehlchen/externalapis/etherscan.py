import json
import logging
import operator
from abc import ABC
from collections.abc import Iterator
from enum import Enum, auto
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, overload

import gevent
import requests

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.binance_sc.constants import BINANCE_SC_GENESIS
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.scroll.constants import SCROLL_GENESIS
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.constants import EVMTX_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_transaction,
    deserialize_int_from_str,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    SUPPORTED_EVM_CHAINS_TYPE,
    ApiKey,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    Location,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.misc import hexstr_to_int, set_user_agent
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

ETHERSCAN_QUERY_LIMIT = 10000
TRANSACTIONS_BATCH_NUM = 10

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HasChainActivity(Enum):
    """
    Classify the type of transaction first found in blockscout/etherscan.
    TRANSACTIONS means that the endpoint for transactions/internal transactions
    had entries, TOKENS means that the tokens endpoint had entries, BALANCE means
    that the address has a non-zero native asset balance and NONE means that no
    activity was found."""
    TRANSACTIONS = auto()
    TOKENS = auto()
    BALANCE = auto()
    NONE = auto()


def _hashes_tuple_to_list(hashes: set[tuple[EVMTxHash, Timestamp]]) -> list[EVMTxHash]:
    """Turns the set of hashes/timestamp to a timestamp ascending ordered list

    This function needs to exist since Set has no guaranteed order of iteration.
    """
    return [x[0] for x in sorted(hashes, key=operator.itemgetter(1))]


ROTKI_PACKAGED_KEY: Final = 'W9CEV6QB9NIPUEHD6KNEYM4PDX6KBPRVVR'


class Etherscan(ExternalServiceWithApiKey, ABC):
    """Base class for all Etherscan implementations"""
    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            chain: SUPPORTED_EVM_CHAINS_TYPE,
    ) -> None:
        super().__init__(database=database, service_name=ExternalService.ETHERSCAN)
        self.msg_aggregator = msg_aggregator
        self.chain = chain
        self.session = create_session()
        self.warning_given = False
        set_user_agent(self.session)
        self.timestamp_to_block_cache: LRUCacheWithRemove[Timestamp, int] = LRUCacheWithRemove(maxsize=32)  # noqa: E501
        # set per-chain earliest timestamps that can be turned to blocks. Never returns block 0
        match self.chain:
            case SupportedBlockchain.ETHEREUM:
                self.earliest_ts = 1438269989
            case SupportedBlockchain.OPTIMISM:
                self.earliest_ts = 1636665399
            case SupportedBlockchain.ARBITRUM_ONE:
                self.earliest_ts = 1622243344
            case SupportedBlockchain.BASE:
                self.earliest_ts = 1686789347
            case SupportedBlockchain.GNOSIS:
                self.earliest_ts = 1539024185
            case SupportedBlockchain.SCROLL:
                self.earliest_ts = SCROLL_GENESIS
            case SupportedBlockchain.BINANCE_SC:
                self.earliest_ts = BINANCE_SC_GENESIS
            case SupportedBlockchain.POLYGON_POS:
                self.earliest_ts = 1590856200

        self.api_url = 'https://api.etherscan.io/v2/api'
        self.base_query_args = {'chainid': str(self.chain.to_chain_id().serialize())}

    @overload
    def _query(
            self,
            module: str,
            action: Literal[
                'balancemulti',
                'txlist',
                'txlistinternal',
                'tokentx',
                'getLogs',
                'txsBeaconWithdrawal',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @overload
    def _query(
            self,
            module: str,
            action: Literal[
                'eth_getTransactionReceipt',
                'eth_getTransactionByHash',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        ...

    @overload
    def _query(
            self,
            module: str,
            action: Literal[
                'getcontractcreation',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | None:
        ...

    @overload
    def _query(
            self,
            module: str,
            action: Literal[
                'getabi',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> str | None:
        ...

    @overload
    def _query(
            self,
            module: str,
            action: Literal[
                'eth_getBlockByNumber',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        ...

    @overload
    def _query(
            self,
            module: str,
            action: Literal[
                'balance',
                'tokenbalance',
                'eth_blockNumber',
                'eth_getCode',
                'eth_call',
                'getblocknobytime',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> str:
        ...

    def _query(
            self,
            module: str,
            action: str,
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | (str | (list[EvmTransaction] | (dict[str, Any] | None))):
        """Queries etherscan

        None is a valid result for this function when the requested information doesn't exist.
        Happens when asking for the code of a contract, transaction by hash, receipt...

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned. Also in the case of exhausting the backoff time.
        """
        result = None
        api_key = self._get_api_key()
        if api_key is None:
            if not self.warning_given:
                self.msg_aggregator.add_message(
                    message_type=WSMessageType.MISSING_API_KEY,
                    data={'service': ExternalService.ETHERSCAN.serialize()},
                )
                self.warning_given = True

            api_key = ApiKey(ROTKI_PACKAGED_KEY)
            log.debug(f'Using default etherscan key for {self.chain}')

        params = {'module': module, 'action': action, 'apikey': api_key} | self.base_query_args
        if options:
            params.update(options)

        backoff = 1
        cached_settings = CachedSettings()
        timeout = timeout or cached_settings.get_timeout_tuple()
        backoff_limit = cached_settings.get_query_retry_limit()  # max time spent trying to get a response from etherscan in case of rate limits  # noqa: E501
        response = None
        while backoff < backoff_limit:
            log.debug(f'Querying {self.chain} etherscan: {self.api_url} with params: {params}')
            try:
                response = self.session.get(url=self.api_url, params=params, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'{self.chain} Etherscan API request failed due to {e!s}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if backoff >= backoff_limit:
                    raise RemoteError(
                        f'Getting {self.chain} Etherscan too many requests error '
                        f'even after we incrementally backed off',
                    )

                log.debug(
                    f'Got too many requests error from {self.chain} etherscan. Will '
                    f'backoff for {backoff} seconds.',
                )
                gevent.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code != 200:
                raise RemoteError(
                    f'{self.chain} Etherscan API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            try:
                json_ret = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'{self.chain} Etherscan API request {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            try:
                if (result := json_ret.get('result')) is None:
                    if action in {'eth_getTransactionByHash', 'eth_getTransactionReceipt', 'getcontractcreation'}:  # noqa: E501
                        return None

                    raise RemoteError(
                        f'Unexpected format of {self.chain} Etherscan response for request {response.url}. '  # noqa: E501
                        f'Missing a result in response. Response was: {response.text}',
                    )

                # successful proxy calls do not include a status
                status = int(json_ret.get('status', 1))

                if status != 1:
                    if status == 0:
                        if result == 'Contract source code not verified':
                            return None
                        if json_ret.get('message', '') == 'NOTOK':
                            if result.startswith(('Max calls per sec rate', 'Max rate limit reached')):  # different variants of the same message found in the different versions. Sent when there is a short 5 secs rate limit.  # noqa: E501
                                log.debug(
                                    f'Got response: {response.text} from {self.chain} etherscan.'
                                    f' Will backoff for {backoff} seconds.',
                                )
                                gevent.sleep(backoff)
                                backoff *= 2
                                continue

                            elif result.startswith('Max daily'):
                                raise RemoteError('Etherscan max daily rate limit reached.')

                    transaction_endpoint_and_none_found = (
                        status == 0 and
                        json_ret['message'] == 'No transactions found' and
                        action in {'txlist', 'txlistinternal', 'tokentx', 'txsBeaconWithdrawal'}
                    )
                    logs_endpoint_and_none_found = (
                        status == 0 and
                        json_ret['message'] == 'No records found' and
                        'getLogs' in action
                    )
                    if transaction_endpoint_and_none_found or logs_endpoint_and_none_found:
                        return []

                    # else
                    raise RemoteError(f'{self.chain} Etherscan returned error response: {json_ret}')  # noqa: E501
            except KeyError as e:
                raise RemoteError(
                    f'Unexpected format of {self.chain} Etherscan response for request {response.url}. '  # noqa: E501
                    f'Missing key entry for {e!s}. Response was: {response.text}',
                ) from e

            # success, break out of the loop and return result
            return result

        # will only run if we get out of the loop due to backoff limit
        assert response is not None, 'This loop always runs at least once and response is not None'
        msg = (
            f'{self.chain} etherscan API request to {response.url} failed due to backing'
            ' off for more than the backoff limit'
        )
        log.error(msg)
        raise RemoteError(msg)

    def _process_timestamp_or_blockrange(self, period: TimestampOrBlockRange, options: dict[str, Any]) -> dict[str, Any]:  # noqa: E501
        """Process TimestampOrBlockRange and populate call options"""
        if period.range_type == 'blocks':
            from_block = period.from_value
            to_block = period.to_value
        else:  # timestamps
            from_block = self.get_blocknumber_by_time(
                ts=period.from_value,  # type: ignore
                closest='before',
            )
            to_block = self.get_blocknumber_by_time(
                ts=period.to_value,  # type: ignore
                closest='before',
            )

        options['startBlock'] = str(from_block)
        options['endBlock'] = str(to_block)
        return options

    def _maybe_paginate(self, result: list[dict[str, Any]], options: dict[str, Any]) -> dict[str, Any] | None:  # noqa: E501
        """Check if the results have hit the pagination limit.
        If yes adjust the options accordingly. Otherwise signal we are done"""
        if len(result) != ETHERSCAN_QUERY_LIMIT:
            return None

        # else we hit the limit. Query once more with startBlock being the last
        # block we got. There may be duplicate entries if there are more than one
        # entries for that last block but they should be filtered
        # out when we input all of these in the DB
        last_block = result[-1]['blockNumber']
        options['startBlock'] = last_block
        return options

    @overload
    def get_transactions(
            self,
            account: ChecksumEvmAddress | None,
            action: Literal['txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmInternalTransaction]]:
        ...

    @overload
    def get_transactions(
            self,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]]:
        ...

    def get_transactions(
            self,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Gets a list of transactions (either normal or internal) for an account.

        Can specify a given timestamp or block period.

        For internal transactions can also query by parent transaction hash instead
        Also the account is optional in case of internal transactions.

        May raise:
        - RemoteError due to self._query(). Also if the returned result
        is not in the expected format
        """
        options = {'sort': 'asc'}
        parent_tx_hash = None
        if account:
            options['address'] = str(account)
        if period_or_hash is not None:
            if isinstance(period_or_hash, TimestampOrBlockRange):
                options = self._process_timestamp_or_blockrange(period_or_hash, options)
            else:  # has to be parent transaction hash and internal transaction
                options['txHash'] = period_or_hash.hex()
                parent_tx_hash = period_or_hash

        transactions: list[EvmTransaction] | list[EvmInternalTransaction] = []
        is_internal = action == 'txlistinternal'
        chain_id = self.chain.to_chain_id()
        while True:
            result = self._query(module='account', action=action, options=options)
            if len(result) == 0:
                log.debug('Length of etherscan account result is 0. Breaking out of the query')
                break

            last_ts = deserialize_timestamp(result[0]['timeStamp'])
            for entry in result:
                try:  # Handle normal transactions. Internal dict does not contain a hash sometimes
                    if is_internal or entry['hash'].startswith('GENESIS') is False:
                        tx, _ = deserialize_evm_transaction(  # type: ignore
                            data=entry,
                            internal=is_internal,
                            chain_id=chain_id,
                            evm_inquirer=None,
                            parent_tx_hash=parent_tx_hash,
                        )
                        tx = self._additional_transaction_processing(tx)
                    else:  # Handling genesis transactions
                        assert self.db is not None, 'self.db should exists at this point'
                        dbtx = DBEvmTx(self.db)
                        tx = dbtx.get_or_create_genesis_transaction(
                            account=account,  # type: ignore[arg-type]  # always exists here
                            chain_id=chain_id,  # type: ignore[arg-type]  # is only supported chain
                        )
                        trace_id = dbtx.get_max_genesis_trace_id(chain_id)
                        entry['from'] = ZERO_ADDRESS
                        entry['hash'] = GENESIS_HASH
                        entry['traceId'] = trace_id
                        internal_tx, _ = deserialize_evm_transaction(
                            data=entry,
                            internal=True,
                            chain_id=chain_id,
                            evm_inquirer=None,
                        )
                        with self.db.user_write() as cursor:
                            dbtx.add_evm_internal_transactions(
                                write_cursor=cursor,
                                transactions=[internal_tx],
                                relevant_address=None,  # can't know the address here
                            )

                        dbevents = DBHistoryEvents(self.db)
                        with self.db.user_write() as write_cursor:
                            # Delete decoded genesis events so they can be later redecoded.
                            dbevents.delete_events_by_tx_hash(
                                write_cursor=write_cursor,
                                tx_hashes=[GENESIS_HASH],
                                location=Location.from_chain(self.chain),
                            )
                            write_cursor.execute(
                                'DELETE from evm_tx_mappings WHERE tx_id=(SELECT identifier FROM '
                                'evm_transactions WHERE tx_hash=? AND chain_id=?) AND value=?',
                                (GENESIS_HASH, self.chain.to_chain_id().serialize_for_db(), EVMTX_DECODED),  # noqa: E501
                            )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(f'{e!s}. Skipping transaction')
                    continue

                timestamp = deserialize_timestamp(entry['timeStamp'])
                if timestamp > last_ts and len(transactions) >= TRANSACTIONS_BATCH_NUM:
                    yield transactions
                    last_ts = timestamp
                    transactions = []
                transactions.append(tx)

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        yield transactions

    def get_token_transaction_hashes(
            self,
            account: ChecksumEvmAddress,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
    ) -> Iterator[list[EVMTxHash]]:
        options = {'address': str(account), 'sort': 'asc'}
        if from_ts is not None:
            from_block = self.get_blocknumber_by_time(ts=from_ts, closest='before')
            options['startBlock'] = str(from_block)
        if to_ts is not None:
            to_block = self.get_blocknumber_by_time(ts=to_ts, closest='before')
            options['endBlock'] = str(to_block)

        hashes: set[tuple[EVMTxHash, Timestamp]] = set()
        while True:
            result = self._query(module='account', action='tokentx', options=options)
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if (result and len(result) != 0) else None  # noqa: E501
            for entry in result:
                try:
                    timestamp = deserialize_timestamp(entry['timeStamp'])
                except DeserializationError as e:
                    log.error(
                        f"Failed to read transaction timestamp {entry['hash']} from {self.chain} "
                        f'etherscan for {account} in the range {from_ts} to {to_ts}. {e!s}',
                    )
                    continue

                if timestamp > last_ts and len(hashes) >= TRANSACTIONS_BATCH_NUM:  # type: ignore
                    yield _hashes_tuple_to_list(hashes)
                    hashes = set()
                    last_ts = timestamp
                try:
                    hashes.add((deserialize_evm_tx_hash(entry['hash']), timestamp))
                except DeserializationError as e:
                    log.error(
                        f"Failed to read transaction hash {entry['hash']} from {self.chain} "
                        f'etherscan for {account} in the range {from_ts} to {to_ts}. {e!s}',
                    )
                    continue

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        yield _hashes_tuple_to_list(hashes)

    def has_activity(self, account: ChecksumEvmAddress) -> HasChainActivity:
        """Queries native asset balance, transactions, internal_txs and tokentx for an address
        with limit=1 just to quickly determine if the account has had any activity in the chain.
        We make a distinction between transactions and ERC20 transfers since ERC20
        are often spammed. If there was no activity at all we return the enum value
        NONE.
        """
        options = {'address': str(account), 'page': 1, 'offset': 1}
        result = self._query(module='account', action='txlist', options=options)
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS
        result = self._query(module='account', action='txlistinternal', options=options)
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS
        result = self._query(module='account', action='tokentx', options=options)
        if len(result) != 0:
            return HasChainActivity.TOKENS
        if self.chain in {SupportedBlockchain.ETHEREUM, SupportedBlockchain.GNOSIS}:
            balance = self._query(module='account', action='balance', options={'address': account})
            if int(balance) != 0:
                return HasChainActivity.BALANCE
        return HasChainActivity.NONE

    def get_latest_block_number(self) -> int:
        """Gets the latest block number

        May raise:
        - RemoteError due to self._query().
        """
        result = self._query(
            module='proxy',
            action='eth_blockNumber',
        )
        return int(result, 16)

    def get_block_by_number(self, block_number: int) -> dict[str, Any]:
        """
        Gets a block object by block number

        May raise:
        - RemoteError due to self._query().
        """
        options = {'tag': hex(block_number), 'boolean': 'true'}
        block_data = self._query(module='proxy', action='eth_getBlockByNumber', options=options)
        # We need to convert some data from hex here
        # https://github.com/PyCQA/pylint/issues/4739
        block_data['timestamp'] = hexstr_to_int(block_data['timestamp'])
        block_data['number'] = hexstr_to_int(block_data['number'])

        return block_data

    def get_transaction_by_hash(self, tx_hash: EVMTxHash) -> dict[str, Any] | None:
        """
        Gets a transaction object by hash

        May raise:
        - RemoteError due to self._query().
        """
        options = {'txhash': tx_hash.hex()}
        return self._query(module='proxy', action='eth_getTransactionByHash', options=options)

    def get_code(self, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        return self._query(module='proxy', action='eth_getCode', options={'address': account})

    def get_transaction_receipt(self, tx_hash: EVMTxHash) -> dict[str, Any] | None:
        """Gets the receipt for the given transaction hash

        May raise:
        - RemoteError due to self._query().
        """
        return self._query(
            module='proxy',
            action='eth_getTransactionReceipt',
            options={'txhash': tx_hash.hex()},
        )

    def eth_call(
            self,
            to_address: ChecksumEvmAddress,
            input_data: str,
    ) -> str:
        """Performs an eth_call on the given address and the given input data.

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        options = {'to': to_address, 'data': input_data}
        return self._query(
            module='proxy',
            action='eth_call',
            options=options,
        )

    def get_logs(
            self,
            contract_address: ChecksumEvmAddress,
            topics: list[str],
            from_block: int,
            to_block: int | str = 'latest',
    ) -> list[dict[str, Any]]:
        """Performs the etherscan style of eth_getLogs as explained here:
        https://etherscan.io/apis#logs

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        options = {'fromBlock': from_block, 'toBlock': to_block, 'address': contract_address}
        for idx, topic in enumerate(topics):
            if topic is not None:
                options[f'topic{idx}'] = topic
                options[f'topic{idx}_{idx + 1}opr'] = 'and'

        timeout_tuple = CachedSettings().get_timeout_tuple()
        return self._query(
            module='logs',
            action='getLogs',
            options=options,
            timeout=(timeout_tuple[0], timeout_tuple[1] * 2),
        )

    def get_blocknumber_by_time(self, ts: Timestamp, closest: Literal['before', 'after'] = 'before') -> int:  # noqa: E501
        """Performs the etherscan api call to get the blocknumber by a specific timestamp

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        if ts < self.earliest_ts:
            return 0  # etherscan does not handle timestamps close to genesis well

        # check if value exists in the cache
        if (block_number := self.timestamp_to_block_cache.get(ts)) is not None:
            return block_number

        options = {'timestamp': ts, 'closest': closest}
        result = self._query(
            module='block',
            action='getblocknobytime',
            options=options,
        )
        try:
            number = deserialize_int_from_str(result, 'etherscan getblocknobytime')
        except DeserializationError as e:
            raise RemoteError(
                f'Could not read blocknumber from {self.chain} etherscan '
                f'getblocknobytime result {result}',
            ) from e

        self.timestamp_to_block_cache.add(key=ts, value=number)
        return number

    def get_contract_creation_hash(self, address: ChecksumEvmAddress) -> EVMTxHash | None:
        """Get the contract creation block from etherscan for the given address.

        Returns `None` if the address is not a contract.

        May raise:
        - RemoteError in case of problems contacting etherscan.
        """
        options = {'contractaddresses': address}
        result = self._query(
            module='contract',
            action='getcontractcreation',
            options=options,
        )
        return deserialize_evm_tx_hash(result[0]['txHash']) if result is not None else None

    def get_contract_abi(self, address: ChecksumEvmAddress) -> str | None:
        """Get the contract abi from etherscan for the given address if verified.

        Returns `None` if the address is not a verified contract.

        May raise:
        - RemoteError in case of problems contacting etherscan
        """
        options = {'address': address}
        result = self._query(
            module='contract',
            action='getabi',
            options=options,
        )
        if result is None:
            return None

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None

    def _additional_transaction_processing(self, tx: EvmTransaction | EvmInternalTransaction) -> EvmTransaction | EvmInternalTransaction:  # noqa: E501
        """Performs additional processing on chain-specific tx attributes"""
        return tx
