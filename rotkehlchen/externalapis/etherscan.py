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
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.externalapis.utils import get_earliest_ts
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_transaction,
    deserialize_fval,
    deserialize_int_from_str,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import from_gwei, hexstr_to_int, set_user_agent, ts_sec_to_ms
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
    ) -> None:
        super().__init__(database=database, service_name=ExternalService.ETHERSCAN)
        self.msg_aggregator = msg_aggregator
        self.session = create_session()
        self.warning_given = False
        set_user_agent(self.session)
        self.api_url = 'https://api.etherscan.io/v2/api'

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id: SUPPORTED_CHAIN_IDS,
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
            log.debug('Using default etherscan key')

        params = {
            'module': module,
            'action': action, 'apikey': api_key,
            'chainid': str(chain_id.serialize()),
        }
        if options:
            params.update(options)

        backoff = 1
        cached_settings = CachedSettings()
        timeout = timeout or cached_settings.get_timeout_tuple()
        backoff_limit = cached_settings.get_query_retry_limit()  # max time spent trying to get a response from etherscan in case of rate limits  # noqa: E501
        response = None
        while backoff < backoff_limit:
            log.debug(f'Querying etherscan for {chain_id}: {self.api_url} with params: {params}')
            try:
                response = self.session.get(url=self.api_url, params=params, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Etherscan API request failed due to {e!s}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if backoff >= backoff_limit:
                    raise RemoteError(
                        'Getting Etherscan too many requests error '
                        f'even after we incrementally backed off while querying {chain_id}',
                    )

                log.debug(
                    f'Got too many requests error from {chain_id} etherscan. Will '
                    f'backoff for {backoff} seconds.',
                )
                gevent.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code != 200:
                raise RemoteError(
                    f'Etherscan API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            try:
                json_ret = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Etherscan API request {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            try:
                if (result := json_ret.get('result')) is None:
                    if action in {'eth_getTransactionByHash', 'eth_getTransactionReceipt', 'getcontractcreation'}:  # noqa: E501
                        return None

                    raise RemoteError(
                        f'Unexpected format of Etherscan response for request {response.url}. '
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
                                    f'Got response: {response.text} from etherscan while '
                                    f'querying chain {chain_id}. Will backoff for {backoff} seconds.',  # noqa: E501
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
                    raise RemoteError(f'{chain_id} Etherscan returned error response: {json_ret}')
            except KeyError as e:
                raise RemoteError(
                    f'Unexpected format of {chain_id} Etherscan response for request {response.url}. '  # noqa: E501
                    f'Missing key entry for {e!s}. Response was: {response.text}',
                ) from e

            # success, break out of the loop and return result
            return result

        # will only run if we get out of the loop due to backoff limit
        assert response is not None, 'This loop always runs at least once and response is not None'
        msg = (
            f'{chain_id} etherscan API request to {response.url} failed due to backing'
            ' off for more than the backoff limit'
        )
        log.error(msg)
        raise RemoteError(msg)

    def _process_timestamp_or_blockrange(self, chain_id: SUPPORTED_CHAIN_IDS, period: TimestampOrBlockRange, options: dict[str, Any]) -> dict[str, Any]:  # noqa: E501
        """Process TimestampOrBlockRange and populate call options"""
        if period.range_type == 'blocks':
            from_block = period.from_value
            to_block = period.to_value
        else:  # timestamps
            from_block = self.get_blocknumber_by_time(
                chain_id=chain_id,
                ts=period.from_value,  # type: ignore
                closest='before',
            )
            to_block = self.get_blocknumber_by_time(
                chain_id=chain_id,
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
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmInternalTransaction]]:
        ...

    @overload
    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]]:
        ...

    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
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
                options = self._process_timestamp_or_blockrange(
                    chain_id=chain_id,
                    period=period_or_hash,
                    options=options,
                )
            else:  # has to be parent transaction hash and internal transaction
                options['txHash'] = period_or_hash.hex()
                parent_tx_hash = period_or_hash

        transactions: list[EvmTransaction] | list[EvmInternalTransaction] = []
        is_internal = action == 'txlistinternal'

        while True:
            result = self._query(
                chain_id=chain_id,
                module='account',
                action=action,
                options=options,
            )
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
                    else:  # Handling genesis transactions
                        assert self.db is not None, 'self.db should exists at this point'
                        dbtx = DBEvmTx(self.db)
                        tx = dbtx.get_or_create_genesis_transaction(
                            account=account,  # type: ignore[arg-type]  # always exists here
                            chain_id=chain_id,
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
                            dbevents.delete_events_by_tx_ref(
                                write_cursor=write_cursor,
                                tx_refs=[GENESIS_HASH],
                                location=Location.from_chain_id(chain_id.to_blockchain()),  # type: ignore
                            )
                            write_cursor.execute(
                                'DELETE from evm_tx_mappings WHERE tx_id=(SELECT identifier FROM '
                                'evm_transactions WHERE tx_hash=? AND chain_id=?) AND value=?',
                                (GENESIS_HASH, chain_id.serialize_for_db(), TX_DECODED),
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
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[EVMTxHash]]:
        options = {'address': str(account), 'sort': 'asc'}
        if from_block is not None:
            options['startBlock'] = str(from_block)
        if to_block is not None:
            options['endBlock'] = str(to_block)

        hashes: set[tuple[EVMTxHash, Timestamp]] = set()
        while True:
            result = self._query(
                chain_id=chain_id,
                module='account',
                action='tokentx',
                options=options,
            )
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if (result and len(result) != 0) else None  # noqa: E501
            for entry in result:
                try:
                    timestamp = deserialize_timestamp(entry['timeStamp'])
                except DeserializationError as e:
                    log.error(
                        f"Failed to read transaction timestamp {entry['hash']} from {chain_id} "
                        f'etherscan for {account} in the range {from_block} to {to_block}. {e!s}',
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
                        f"Failed to read transaction hash {entry['hash']} from {chain_id} "
                        f'etherscan for {account} in the range {from_block} to {to_block}. {e!s}',
                    )
                    continue

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        yield _hashes_tuple_to_list(hashes)

    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> HasChainActivity:
        """Queries native asset balance, transactions, internal_txs and tokentx for an address
        with limit=1 just to quickly determine if the account has had any activity in the chain.
        We make a distinction between transactions and ERC20 transfers since ERC20
        are often spammed. If there was no activity at all we return the enum value
        NONE.
        """
        options = {'address': str(account), 'page': 1, 'offset': 1}
        result = self._query(chain_id=chain_id, module='account', action='txlist', options=options)
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS
        result = self._query(chain_id=chain_id, module='account', action='txlistinternal', options=options)  # noqa: E501
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS
        result = self._query(chain_id=chain_id, module='account', action='tokentx', options=options)  # noqa: E501
        if len(result) != 0:
            return HasChainActivity.TOKENS
        if chain_id in {ChainID.ETHEREUM, ChainID.GNOSIS}:
            balance = self._query(
                chain_id=chain_id,
                module='account',
                action='balance',
                options={'address': account},
            )
            if int(balance) != 0:
                return HasChainActivity.BALANCE
        return HasChainActivity.NONE

    def get_latest_block_number(self, chain_id: SUPPORTED_CHAIN_IDS) -> int:
        """Gets the latest block number

        May raise:
        - RemoteError due to self._query().
        """
        result = self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_blockNumber',
        )
        return int(result, 16)

    def get_block_by_number(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            block_number: int,
    ) -> dict[str, Any]:
        """
        Gets a block object by block number

        May raise:
        - RemoteError due to self._query().
        """
        options = {'tag': hex(block_number), 'boolean': 'true'}
        block_data = self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getBlockByNumber',
            options=options,
        )
        # We need to convert some data from hex here
        # https://github.com/PyCQA/pylint/issues/4739
        block_data['timestamp'] = hexstr_to_int(block_data['timestamp'])
        block_data['number'] = hexstr_to_int(block_data['number'])

        return block_data

    def get_transaction_by_hash(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            tx_hash: EVMTxHash,
    ) -> dict[str, Any] | None:
        """
        Gets a transaction object by hash

        May raise:
        - RemoteError due to self._query().
        """
        options = {'txhash': tx_hash.hex()}
        return self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getTransactionByHash',
            options=options,
        )

    def get_code(self, chain_id: SUPPORTED_CHAIN_IDS, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        return self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getCode',
            options={'address': account},
        )

    def get_transaction_receipt(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            tx_hash: EVMTxHash,
    ) -> dict[str, Any] | None:
        """Gets the receipt for the given transaction hash

        May raise:
        - RemoteError due to self._query().
        """
        return self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getTransactionReceipt',
            options={'txhash': tx_hash.hex()},
        )

    def eth_call(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id=chain_id,
            module='proxy',
            action='eth_call',
            options=options,
        )

    def get_logs(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
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
            chain_id=chain_id,
            module='logs',
            action='getLogs',
            options=options,
            timeout=(timeout_tuple[0], timeout_tuple[1] * 2),
        )

    def get_blocknumber_by_time(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            ts: Timestamp,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Performs the etherscan api call to get the blocknumber by a specific timestamp

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        # set per-chain earliest timestamps that can be turned to blocks. Never returns block 0
        if ts < get_earliest_ts(chain_id):
            return 0  # etherscan does not handle timestamps close to genesis well

        options = {'timestamp': ts, 'closest': closest}
        result = self._query(
            chain_id=chain_id,
            module='block',
            action='getblocknobytime',
            options=options,
        )
        try:
            number = deserialize_int_from_str(result, 'etherscan getblocknobytime')
        except DeserializationError as e:
            raise RemoteError(
                f'Could not read blocknumber from etherscan for {chain_id}  '
                f'getblocknobytime result {result}',
            ) from e

        return number

    def get_contract_creation_hash(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> EVMTxHash | None:
        """Get the contract creation block from etherscan for the given address.

        Returns `None` if the address is not a contract.

        May raise:
        - RemoteError in case of problems contacting etherscan.
        """
        options = {'contractaddresses': address}
        result = self._query(
            chain_id=chain_id,
            module='contract',
            action='getcontractcreation',
            options=options,
        )
        return deserialize_evm_tx_hash(result[0]['txHash']) if result is not None else None

    def get_contract_abi(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> str | None:
        """Get the contract abi from etherscan for the given address if verified.

        Returns `None` if the address is not a verified contract.

        May raise:
        - RemoteError in case of problems contacting etherscan
        """
        options = {'address': address}
        result = self._query(
            chain_id=chain_id,
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

    def maybe_get_l1_fees(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int | None:
        """Attempt to retrieve L1 fees from etherscan for the given tx via the txlist endpoint."""
        tx_hash_str = tx_hash.hex()
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
            if raw_tx.get('hash') != tx_hash_str:
                continue  # skip unrelated txs for this account in the same block

            try:
                return int(raw_tx['L1FeesPaid'])
            except (KeyError, ValueError) as e:
                msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
                log.error(
                    'Failed to retrieve L1 fees from etherscan txlist for '
                    f'{chain_id.to_name()} tx {tx_hash_str} due to {msg}',
                )
                break

        return None
