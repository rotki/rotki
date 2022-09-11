import logging
from json.decoder import JSONDecodeError
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    overload,
)

import gevent
import requests

from rotkehlchen.chain.ethereum.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.constants.timing import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_TIMEOUT_TUPLE,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ethtx import DBEthTx
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
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_int
from rotkehlchen.utils.serialization import jsonloads_dict

ETHERSCAN_TX_QUERY_LIMIT = 10000
TRANSACTIONS_BATCH_NUM = 10

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _hashes_tuple_to_list(hashes: Set[Tuple[str, Timestamp]]) -> List[str]:
    """Turns the set of hashes/timestamp to a timestamp ascending ordered list

    This function needs to exist since Set has no guranteed order of iteration.
    """
    return [x[0] for x in sorted(hashes, key=lambda x: x[1])]


class Etherscan(ExternalServiceWithApiKey):
    def __init__(self, database: DBHandler, msg_aggregator: MessagesAggregator) -> None:
        super().__init__(database=database, service_name=ExternalService.ETHERSCAN)
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        self.warning_given = False
        self.session.headers.update({'User-Agent': 'rotkehlchen'})

    @overload
    def _query(  # pylint: disable=no-self-use
            self,
            module: str,
            action: Literal[
                'balancemulti',
                'txlist',
                'txlistinternal',
                'tokentx',
                'getLogs',
            ],
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @overload
    def _query(  # pylint: disable=no-self-use
            self,
            module: str,
            action: Literal[
                'eth_getBlockByNumber',
                'eth_getTransactionReceipt',
                'eth_getTransactionByHash',
            ],
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        ...

    @overload
    def _query(  # pylint: disable=no-self-use
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
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> str:
        ...

    def _query(
            self,
            module: str,
            action: str,
            options: Optional[Dict[str, Any]] = None,
            timeout: Optional[Tuple[int, int]] = None,
    ) -> Union[List[Dict[str, Any]], str, List[EvmTransaction], Dict[str, Any]]:
        """Queries etherscan

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        query_str = f'https://api.etherscan.io/api?module={module}&action={action}'
        if options:
            for name, value in options.items():
                query_str += f'&{name}={value}'

        api_key = self._get_api_key()
        if api_key is None:
            if not self.warning_given:
                self.msg_aggregator.add_warning(
                    'You do not have an Etherscan API key configured. rotki '
                    'etherscan queries will still work but will be very slow. '
                    'If you are not using your own ethereum node, it is recommended '
                    'to go to https://etherscan.io/register, create an API '
                    'key and then input it in the external service credentials setting of rotki',
                )
                self.warning_given = True
        else:
            query_str += f'&apikey={api_key}'

        backoff = 1
        backoff_limit = 33
        while backoff < backoff_limit:
            log.debug(f'Querying etherscan: {query_str}')
            try:
                response = self.session.get(query_str, timeout=timeout if timeout else DEFAULT_TIMEOUT_TUPLE)  # noqa: E501
            except requests.exceptions.RequestException as e:
                if 'Max retries exceeded with url' in str(e):
                    log.debug(
                        f'Got max retries exceeded from etherscan. Will '
                        f'backoff for {backoff} seconds.',
                    )
                    gevent.sleep(backoff)
                    backoff = backoff * 2
                    if backoff >= backoff_limit:
                        raise RemoteError(
                            'Getting Etherscan max connections error even '
                            'after we incrementally backed off',
                        ) from e
                    continue

                raise RemoteError(f'Etherscan API request failed due to {str(e)}') from e

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
                result = json_ret.get('result', None)
                if result is None:
                    raise RemoteError(
                        f'Unexpected format of Etherscan response for request {response.url}. '
                        f'Missing a result in response. Response was: {response.text}',
                    )

                # sucessful proxy calls do not include a status
                status = int(json_ret.get('status', 1))

                if status != 1:
                    if status == 0 and 'rate limit reached' in result:
                        log.debug(
                            f'Got response: {response.text} from etherscan. Will '
                            f'backoff for {backoff} seconds.',
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
                    raise RemoteError(f'Etherscan returned error response: {json_ret}')
            except KeyError as e:
                raise RemoteError(
                    f'Unexpected format of Etherscan response for request {response.url}. '
                    f'Missing key entry for {str(e)}. Response was: {response.text}',
                ) from e

            # success, break out of the loop and return result
            return result

        return result

    @overload
    def get_transactions(
            self,
            account: ChecksumEvmAddress,
            action: Literal['txlistinternal'],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> Iterator[List[EvmInternalTransaction]]:
        ...

    @overload
    def get_transactions(
            self,
            account: ChecksumEvmAddress,
            action: Literal['txlist'],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> Iterator[List[EvmTransaction]]:
        ...

    def get_transactions(
            self,
            account: ChecksumEvmAddress,
            action: Literal['txlist', 'txlistinternal'],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> Union[Iterator[List[EvmTransaction]], Iterator[List[EvmInternalTransaction]]]:
        """Gets a list of transactions (either normal or internal) for account.

        May raise:
        - RemoteError due to self._query(). Also if the returned result
        is not in the expected format
        """
        options = {'address': str(account), 'sort': 'asc'}
        if from_ts is not None:
            from_block = self.get_blocknumber_by_time(from_ts)
            options['startBlock'] = str(from_block)
        if to_ts is not None:
            to_block = self.get_blocknumber_by_time(to_ts)
            options['endBlock'] = str(to_block)

        transactions: Union[Sequence[EvmTransaction], Sequence[EvmInternalTransaction]] = []  # noqa: E501
        is_internal = action == 'txlistinternal'
        while True:
            result = self._query(module='account', action=action, options=options)
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if len(result) != 0 else None  # noqa: E501 pylint: disable=unsubscriptable-object
            for entry in result:
                gevent.sleep(0)
                try:
                    # Handle genesis block transactions
                    if entry['hash'].startswith('GENESIS') is False:
                        tx = deserialize_evm_transaction(  # type: ignore
                            data=entry,
                            internal=is_internal,
                            manager=None,
                        )
                    else:
                        # Handling genesis transactions
                        dbtx = DBEthTx(self.db)  # type: ignore
                        tx = dbtx.get_or_create_genesis_transaction(account=account)
                        trace_id = dbtx.get_max_genesis_trace_id()
                        entry['from'] = ZERO_ADDRESS
                        entry['hash'] = GENESIS_HASH
                        entry['traceId'] = trace_id
                        internal_tx = deserialize_evm_transaction(
                            data=entry,
                            internal=True,
                            manager=None,
                        )
                        with self.db.user_write() as cursor:  # type: ignore  # db always here
                            dbtx.add_ethereum_internal_transactions(
                                write_cursor=cursor,
                                transactions=[internal_tx],
                                relevant_address=account,
                            )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(f'{str(e)}. Skipping transaction')
                    continue

                if tx.timestamp > last_ts and len(transactions) >= TRANSACTIONS_BATCH_NUM:
                    yield transactions
                    last_ts = tx.timestamp
                    transactions = []
                transactions.append(tx)  # type: ignore

            if len(result) != ETHERSCAN_TX_QUERY_LIMIT:
                break
            # else we hit the limit. Query once more with startBlock being the last
            # block we got. There may be duplicate entries if there are more than one
            # transactions for that last block but they should be filtered
            # out when we input all of these in the DB
            last_block = result[-1]['blockNumber']  # pylint: disable=unsubscriptable-object
            options['startBlock'] = last_block

        yield transactions

    def get_token_transaction_hashes(
            self,
            account: ChecksumEvmAddress,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> Iterator[List[str]]:
        options = {'address': str(account), 'sort': 'asc'}
        if from_ts is not None:
            from_block = self.get_blocknumber_by_time(from_ts)
            options['startBlock'] = str(from_block)
        if to_ts is not None:
            to_block = self.get_blocknumber_by_time(to_ts)
            options['endBlock'] = str(to_block)

        hashes: Set[Tuple[str, Timestamp]] = set()
        while True:
            result = self._query(module='account', action='tokentx', options=options)
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if len(result) != 0 else None  # noqa: E501 pylint: disable=unsubscriptable-object
            for entry in result:
                gevent.sleep(0)
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
            last_block = result[-1]['blockNumber']  # pylint: disable=unsubscriptable-object
            options['startBlock'] = last_block

        yield _hashes_tuple_to_list(hashes)

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

    def get_block_by_number(self, block_number: int) -> Dict[str, Any]:
        """
        Gets a block object by block number

        May raise:
        - RemoteError due to self._query().
        """
        options = {'tag': hex(block_number), 'boolean': 'true'}
        block_data = self._query(module='proxy', action='eth_getBlockByNumber', options=options)
        # We need to convert some data from hex here
        # https://github.com/PyCQA/pylint/issues/4739
        block_data['timestamp'] = hex_or_bytes_to_int(block_data['timestamp'])  # pylint: disable=unsubscriptable-object  # noqa: E501
        block_data['number'] = hex_or_bytes_to_int(block_data['number'])  # pylint: disable=unsubscriptable-object  # noqa: E501

        return block_data

    def get_transaction_by_hash(self, tx_hash: EVMTxHash) -> Dict[str, Any]:
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

    def get_transaction_receipt(self, tx_hash: EVMTxHash) -> Dict[str, Any]:
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
            topics: List[str],
            from_block: int,
            to_block: Union[int, str] = 'latest',
    ) -> List[Dict[str, Any]]:
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

    def get_blocknumber_by_time(self, ts: Timestamp) -> int:
        """Performs the etherscan api call to get the blocknumber by a specific timestamp

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        if ts < 1438269989:
            return 0  # etherscan does not handle timestamps close and before genesis well

        options = {'timestamp': ts, 'closest': 'before'}
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
