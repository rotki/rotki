import json
import logging
from abc import ABCMeta
from collections.abc import Iterator
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, overload

import gevent
import requests

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants.timing import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_TIMEOUT_TUPLE,
)
from rotkehlchen.db.constants import HISTORY_MAPPING_STATE_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
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
    SUPPORTED_EVM_CHAINS,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_int, set_user_agent
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

ETHERSCAN_TX_QUERY_LIMIT = 10000
TRANSACTIONS_BATCH_NUM = 10

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _hashes_tuple_to_list(hashes: set[tuple[str, Timestamp]]) -> list[str]:
    """Turns the set of hashes/timestamp to a timestamp ascending ordered list

    This function needs to exist since Set has no guranteed order of iteration.
    """
    return [x[0] for x in sorted(hashes, key=lambda x: x[1])]


class Etherscan(ExternalServiceWithApiKey, metaclass=ABCMeta):
    """Base class for all Etherscan implementations"""
    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            chain: SUPPORTED_EVM_CHAINS,
            base_url: str,
            service: Literal[ExternalService.ETHERSCAN, ExternalService.OPTIMISM_ETHERSCAN],
    ) -> None:
        super().__init__(database=database, service_name=service)
        self.msg_aggregator = msg_aggregator
        self.chain = chain
        self.prefix_url = 'api.' if chain == SupportedBlockchain.ETHEREUM else 'api-'
        self.base_url = base_url
        self.session = requests.session()
        self.warning_given = False
        set_user_agent(self.session)
        # set per-chain earliest timestamps that can be turned to blocks. Never returns block 0
        if service == ExternalService.ETHERSCAN:
            self.earliest_ts = 1438269989
        else:  # Optimism
            self.earliest_ts = 1636665399

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
            ],
            options: Optional[dict[str, Any]] = None,
            timeout: Optional[tuple[int, int]] = None,
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
            options: Optional[dict[str, Any]] = None,
            timeout: Optional[tuple[int, int]] = None,
    ) -> Optional[dict[str, Any]]:
        ...

    @overload
    def _query(
            self,
            module: str,
            action: Literal[
                'getcontractcreation',
            ],
            options: Optional[dict[str, Any]] = None,
            timeout: Optional[tuple[int, int]] = None,
    ) -> Optional[list[dict[str, Any]]]:
        ...

    @overload
    def _query(  # pylint: disable=no-self-use
            self,
            module: str,
            action: Literal[
                'getabi',
            ],
            options: Optional[dict[str, Any]] = None,
            timeout: Optional[tuple[int, int]] = None,
    ) -> Optional[str]:
        ...

    @overload
    def _query(  # pylint: disable=no-self-use
            self,
            module: str,
            action: Literal[
                'eth_getBlockByNumber',
            ],
            options: Optional[dict[str, Any]] = None,
            timeout: Optional[tuple[int, int]] = None,
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
            options: Optional[dict[str, Any]] = None,
            timeout: Optional[tuple[int, int]] = None,
    ) -> str:
        ...

    def _query(
            self,
            module: str,
            action: str,
            options: Optional[dict[str, Any]] = None,
            timeout: Optional[tuple[int, int]] = None,
    ) -> Union[list[dict[str, Any]], str, list[EvmTransaction], dict[str, Any], None]:
        """Queries etherscan

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        query_str = f'https://{self.prefix_url}{self.base_url}/api?module={module}&action={action}'
        if options:
            for name, value in options.items():
                query_str += f'&{name}={value}'

        api_key = self._get_api_key()
        if api_key is None:
            if not self.warning_given:
                self.msg_aggregator.add_message(
                    message_type=WSMessageType.MISSING_API_KEY,
                    data={
                        'service': ExternalService.ETHERSCAN.serialize(),
                        'location': self.chain.to_chain_id().to_name(),
                    },
                )
                self.warning_given = True
        else:
            query_str += f'&apikey={api_key}'

        backoff = 1
        backoff_limit = 33
        while backoff < backoff_limit:
            log.debug(f'Querying {self.chain} etherscan: {query_str}')
            try:
                response = self.session.get(query_str, timeout=timeout if timeout else DEFAULT_TIMEOUT_TUPLE)  # noqa: E501
            except requests.exceptions.RequestException as e:
                if 'Max retries exceeded with url' in str(e):
                    log.debug(
                        f'Got max retries exceeded from {self.chain} etherscan. Will '
                        f'backoff for {backoff} seconds.',
                    )
                    gevent.sleep(backoff)
                    backoff = backoff * 2
                    if backoff >= backoff_limit:
                        raise RemoteError(
                            f'Getting {self.chain} Etherscan max connections error even '
                            f'after we incrementally backed off',
                        ) from e
                    continue

                raise RemoteError(f'{self.chain} Etherscan API request failed due to {str(e)}') from e  # noqa: E501

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
                result = json_ret.get('result', None)
                if result is None:
                    if action in ('eth_getTransactionByHash', 'eth_getTransactionReceipt', 'getcontractcreation'):  # noqa: E501
                        return None

                    raise RemoteError(
                        f'Unexpected format of {self.chain} Etherscan response for request {response.url}. '  # noqa: E501
                        f'Missing a result in response. Response was: {response.text}',
                    )

                # sucessful proxy calls do not include a status
                status = int(json_ret.get('status', 1))

                if status != 1:
                    if status == 0:
                        if result == 'Contract source code not verified':
                            return None
                        if 'rate limit reached' in result:
                            log.debug(
                                f'Got response: {response.text} from {self.chain} etherscan.'
                                f' Will backoff for {backoff} seconds.',
                            )
                            gevent.sleep(backoff)
                            # Continue increasing backoff until limit is reached.
                            # If limit is reached then keep sleeping with the limit.
                            # Etherscan will let the query go through eventually
                            if backoff * 2 < backoff_limit:
                                backoff = backoff * 2
                            continue

                    transaction_endpoint_and_none_found = (
                        status == 0 and
                        json_ret['message'] == 'No transactions found' and
                        action in ('txlist', 'txlistinternal', 'tokentx')
                    )
                    logs_endpoint_and_none_found = (
                        status == 0 and
                        json_ret['message'] == 'No records found' and
                        'getLogs' in action
                    )
                    if transaction_endpoint_and_none_found or logs_endpoint_and_none_found:
                        # Can't realize that result is always a list here so we ignore mypy warning
                        return []  # type: ignore

                    # else
                    raise RemoteError(f'{self.chain} Etherscan returned error response: {json_ret}')  # noqa: E501
            except KeyError as e:
                raise RemoteError(
                    f'Unexpected format of {self.chain} Etherscan response for request {response.url}. '  # noqa: E501
                    f'Missing key entry for {str(e)}. Response was: {response.text}',
                ) from e

            # success, break out of the loop and return result
            return result

        return result

    @overload
    def get_transactions(
            self,
            account: Optional[ChecksumEvmAddress],
            action: Literal['txlistinternal'],
            period_or_hash: Optional[Union[TimestampOrBlockRange, EVMTxHash]] = None,
    ) -> Iterator[list[EvmInternalTransaction]]:
        ...

    @overload
    def get_transactions(
            self,
            account: Optional[ChecksumEvmAddress],
            action: Literal['txlist'],
            period_or_hash: Optional[Union[TimestampOrBlockRange, EVMTxHash]] = None,
    ) -> Iterator[list[EvmTransaction]]:
        ...

    def get_transactions(
            self,
            account: Optional[ChecksumEvmAddress],
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: Optional[Union[TimestampOrBlockRange, EVMTxHash]] = None,
    ) -> Union[Iterator[list[EvmTransaction]], Iterator[list[EvmInternalTransaction]]]:
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
                if period_or_hash.range_type == 'blocks':
                    from_block = period_or_hash.from_value
                    to_block = period_or_hash.to_value
                else:  # timestamps
                    from_block = self.get_blocknumber_by_time(
                        ts=period_or_hash.from_value,  # type: ignore
                        closest='before',
                    )
                    to_block = self.get_blocknumber_by_time(
                        ts=period_or_hash.to_value,  # type: ignore
                        closest='before',
                    )

                options['startBlock'] = str(from_block)
                options['endBlock'] = str(to_block)

            else:  # has to be parent transaction hash and internal transaction
                options['txHash'] = period_or_hash.hex()
                parent_tx_hash = period_or_hash

        transactions: Union[list[EvmTransaction], list[EvmInternalTransaction]] = []  # type: ignore  # noqa: E501
        is_internal = action == 'txlistinternal'
        chain_id = self.chain.to_chain_id()
        while True:
            result = self._query(module='account', action=action, options=options)
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if len(result) != 0 else None
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
                                chain_id=self.chain.to_chain_id(),  # type: ignore[arg-type]
                            )
                            write_cursor.execute(
                                'DELETE from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',  # noqa: E501
                                (GENESIS_HASH, self.chain.to_chain_id().serialize_for_db(), HISTORY_MAPPING_STATE_DECODED),  # noqa: E501
                            )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(f'{str(e)}. Skipping transaction')
                    continue

                if tx.timestamp > last_ts and len(transactions) >= TRANSACTIONS_BATCH_NUM:
                    yield transactions
                    last_ts = tx.timestamp
                    transactions = []  # type: ignore
                transactions.append(tx)

            if len(result) != ETHERSCAN_TX_QUERY_LIMIT:
                break
            # else we hit the limit. Query once more with startBlock being the last
            # block we got. There may be duplicate entries if there are more than one
            # transactions for that last block but they should be filtered
            # out when we input all of these in the DB
            last_block = result[-1]['blockNumber']
            options['startBlock'] = last_block

        yield transactions

    def get_token_transaction_hashes(
            self,
            account: ChecksumEvmAddress,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> Iterator[list[str]]:
        options = {'address': str(account), 'sort': 'asc'}
        if from_ts is not None:
            from_block = self.get_blocknumber_by_time(ts=from_ts, closest='before')
            options['startBlock'] = str(from_block)
        if to_ts is not None:
            to_block = self.get_blocknumber_by_time(ts=to_ts, closest='before')
            options['endBlock'] = str(to_block)

        hashes: set[tuple[str, Timestamp]] = set()
        while True:
            result = self._query(module='account', action='tokentx', options=options)
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if len(result) != 0 else None
            for entry in result:
                timestamp = deserialize_timestamp(entry['timeStamp'])
                if timestamp > last_ts and len(hashes) >= TRANSACTIONS_BATCH_NUM:  # type: ignore
                    yield _hashes_tuple_to_list(hashes)
                    hashes = set()
                    last_ts = timestamp
                hashes.add((entry['hash'], timestamp))

            if len(result) != ETHERSCAN_TX_QUERY_LIMIT:
                break
            # else we hit the limit. Query once more with startBlock being the last
            # block we got. There may be duplicate entries if there are more than one
            # transactions for that last block but they should be filtered
            # out when we input all of these in the DB
            last_block = result[-1]['blockNumber']
            options['startBlock'] = last_block

        yield _hashes_tuple_to_list(hashes)

    def has_activity(self, account: ChecksumEvmAddress) -> bool:
        """Queries transactions, internal_txs and tokentx for an address with limit=1
        just to quickly determine if the account has had any activity in the chain"""
        options = {'address': str(account), 'page': 1, 'offset': 1}
        result = self._query(module='account', action='txlist', options=options)
        if len(result) != 0:
            return True
        result = self._query(module='account', action='txlistinternal', options=options)
        if len(result) != 0:
            return True
        result = self._query(module='account', action='tokentx', options=options)
        if len(result) != 0:
            return True
        return False

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
        block_data['timestamp'] = hex_or_bytes_to_int(block_data['timestamp'])
        block_data['number'] = hex_or_bytes_to_int(block_data['number'])

        return block_data

    def get_transaction_by_hash(self, tx_hash: EVMTxHash) -> Optional[dict[str, Any]]:
        """
        Gets a transaction object by hash

        May raise:
        - RemoteError due to self._query().
        """
        options = {'txhash': tx_hash.hex()}
        transaction_data = self._query(module='proxy', action='eth_getTransactionByHash', options=options)  # noqa: E501
        return transaction_data

    def get_code(self, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        result = self._query(module='proxy', action='eth_getCode', options={'address': account})
        return result

    def get_transaction_receipt(self, tx_hash: EVMTxHash) -> Optional[dict[str, Any]]:
        """Gets the receipt for the given transaction hash

        May raise:
        - RemoteError due to self._query().
        """
        result = self._query(
            module='proxy',
            action='eth_getTransactionReceipt',
            options={'txhash': tx_hash.hex()},
        )
        return result

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
        result = self._query(
            module='proxy',
            action='eth_call',
            options=options,
        )
        return result

    def get_logs(
            self,
            contract_address: ChecksumEvmAddress,
            topics: list[str],
            from_block: int,
            to_block: Union[int, str] = 'latest',
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

        result = self._query(
            module='logs',
            action='getLogs',
            options=options,
            timeout=(DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT * 2),
        )
        return result

    def get_blocknumber_by_time(self, ts: Timestamp, closest: Literal['before', 'after'] = 'before') -> int:  # noqa: E501
        """Performs the etherscan api call to get the blocknumber by a specific timestamp

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        if ts < self.earliest_ts:
            return 0  # etherscan does not handle timestamps close to genesis well

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
                f'Could not read blocknumber from etherscan getblocknobytime '
                f'result {result}',
            ) from e

        return number

    def get_contract_creation_hash(self, address: ChecksumEvmAddress) -> Optional[EVMTxHash]:
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

    def get_contract_abi(self, address: ChecksumEvmAddress) -> Optional[str]:
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
