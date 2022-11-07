import json
import logging
import random
from abc import ABCMeta, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from urllib.parse import urlparse

import requests
from ens import ENS
from eth_abi.exceptions import InsufficientDataBytes
from eth_typing import BlockNumber
from web3 import HTTPProvider, Web3
from web3._utils.abi import get_abi_output_types
from web3._utils.contracts import find_matching_event_abi
from web3._utils.filters import construct_event_filter_params
from web3.datastructures import MutableAttributeDict
from web3.exceptions import (
    BadFunctionCallOutput,
    BadResponseFormat,
    BlockNotFound,
    TransactionNotFound,
)
from web3.types import BlockIdentifier, FilterParams

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.ethereum.types import NodeName, WeightedNode
from rotkehlchen.chain.ethereum.utils import MULTICALL_CHUNKS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ONE
from rotkehlchen.constants.ethereum import ERC20TOKEN_ABI, ERC721TOKEN_ABI, UNIV1_LP_ABI
from rotkehlchen.errors.misc import BlockchainQueryError, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_evm_transaction,
    deserialize_int_from_hex,
)
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    SUPPORTED_BLOCKCHAIN_TO_CHAINID,
    ChecksumEvmAddress,
    EvmTokenKind,
    EvmTransaction,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, get_chunks, hex_or_bytes_to_str
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _is_synchronized(current_block: int, latest_block: int) -> Tuple[bool, str]:
    """ Validate that the evm node is synchronized
            within 20 blocks of latest block

        Returns a tuple (results, message)
            - result: Boolean for confirmation of synchronized
            - message: A message containing information on what the status is.
    """
    message = ''
    if current_block < (latest_block - 20):
        message = (
            f'Found evm node but it is out of sync. {current_block} / '
            f'{latest_block}. Will use etherscan.'
        )
        log.warning(message)
        return False, message

    return True, message


WEB3_LOGQUERY_BLOCK_RANGE = 250000


def _query_web3_get_logs(
        web3: Web3,
        filter_args: FilterParams,
        from_block: int,
        to_block: Union[int, Literal['latest']],
        contract_address: ChecksumEvmAddress,
        event_name: str,
        argument_filters: Dict[str, Any],
        initial_block_range: int,
) -> List[Dict[str, Any]]:
    until_block = web3.eth.block_number if to_block == 'latest' else to_block
    events: List[Dict[str, Any]] = []
    start_block = from_block
    block_range = initial_block_range

    while start_block <= until_block:
        filter_args['fromBlock'] = start_block
        end_block = min(start_block + block_range, until_block)
        filter_args['toBlock'] = end_block
        log.debug(
            'Querying web3 node for contract event',
            contract_address=contract_address,
            event_name=event_name,
            argument_filters=argument_filters,
            from_block=filter_args['fromBlock'],
            to_block=filter_args['toBlock'],
        )
        # As seen in https://github.com/rotki/rotki/issues/1787, the json RPC, if it
        # is infura can throw an error here which we can only parse by catching the  exception
        try:
            new_events_web3: List[Dict[str, Any]] = [dict(x) for x in web3.eth.get_logs(filter_args)]  # noqa: E501
        except (ValueError, KeyError) as e:
            if isinstance(e, ValueError):
                try:
                    decoded_error = json.loads(str(e).replace("'", '"'))
                except json.JSONDecodeError:
                    # reraise the value error if the error is not json
                    raise e from None

                msg = decoded_error.get('message', '')
            else:  # temporary hack for key error seen from pokt
                msg = 'query returned more than 10000 results'

            # errors from: https://infura.io/docs/ethereum/json-rpc/eth-getLogs
            if msg in ('query returned more than 10000 results', 'query timeout exceeded'):
                block_range = block_range // 2
                if block_range < 50:
                    raise  # stop retrying if block range gets too small
                # repeat the query with smaller block range
                continue
            # else, well we tried .. reraise the error
            raise e

        # Turn all HexBytes into hex strings
        for e_idx, event in enumerate(new_events_web3):
            new_events_web3[e_idx]['blockHash'] = event['blockHash'].hex()
            new_topics = []
            for topic in event['topics']:
                new_topics.append(topic.hex())
            new_events_web3[e_idx]['topics'] = new_topics
            new_events_web3[e_idx]['transactionHash'] = event['transactionHash'].hex()

        start_block = end_block + 1
        events.extend(new_events_web3)
        # end of the loop, end of 1 query. Reset the block range to max
        block_range = initial_block_range

    return events


class EvmManager(LockableQueryMixIn, metaclass=ABCMeta):
    """EvmManager defines a basic implementation for EVM chains.

    The child class must implement the following methods:
    - query_highest_block
    - have_archive
    - get_blocknumber_by_time

    The child class may optionally implement the following:
    - logquery_block_range
    """
    def __init__(
            self,
            etherscan: Etherscan,
            msg_aggregator: MessagesAggregator,
            greenlet_manager: GreenletManager,
            connect_at_start: Sequence[WeightedNode],
            database: 'DBHandler',
            etherscan_node: WeightedNode,
            etherscan_node_name: str,
            blockchain: SupportedBlockchain,
            contract_scan: EvmContract,
            contract_multicall: EvmContract,
            contract_multicall_2: EvmContract,
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        super().__init__()
        self.greenlet_manager = greenlet_manager
        self.web3_mapping: Dict[NodeName, Web3] = {}
        self.etherscan = etherscan
        self.msg_aggregator = msg_aggregator
        self.database = database
        self.etherscan_node = etherscan_node
        self.etherscan_node_name = etherscan_node_name
        self.blockchain = blockchain
        self.chain_id = SUPPORTED_BLOCKCHAIN_TO_CHAINID[blockchain]
        self.chain_name = self.chain_id.serialize()
        self.contract_scan = contract_scan
        self.contract_multicall = contract_multicall
        self.contract_multicall_2 = contract_multicall_2
        self.rpc_timeout = rpc_timeout
        self.archive_connection = False
        self.queried_archive_connection = False
        self.connect_to_multiple_nodes(connect_at_start)

        # A cache for the erc20 contract info to not requery same one
        self.contract_info_cache: Dict[ChecksumEvmAddress, Dict[str, Any]] = {}

    def get_multi_balance(
            self,
            accounts: List[ChecksumEvmAddress],
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> Dict[ChecksumEvmAddress, FVal]:
        """Returns a dict with keys being accounts and balances in ETH

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        balances: Dict[ChecksumEvmAddress, FVal] = {}
        log.debug(
            'Querying {self.chain_name} chain for {self.blockchain.value} balance',
            eth_addresses=accounts,
        )
        result = self.contract_scan.call(
            manager=self,
            method_name='etherBalances',
            arguments=[accounts],
            call_order=call_order if call_order is not None else self.default_call_order(),
        )
        balances = {}
        for idx, account in enumerate(accounts):
            balances[account] = from_wei(result[idx])
        return balances

    def connected_to_any_web3(self) -> bool:
        return len(self.web3_mapping) != 0

    def default_call_order(self, skip_etherscan: bool = False) -> List[WeightedNode]:
        """Default call order for evm nodes

        Own node always has preference. Then all other node types are randomly queried
        in sequence depending on a weighted probability.


        Some benchmarks on weighted probability based random selection when compared
        to simple random selection. Benchmark was on blockchain balance querying with
        29 ethereum accounts and at the time 1010 different ethereum tokens.

        With weights: etherscan: 0.5, mycrypto: 0.25, blockscout: 0.2, avado: 0.05
        ===> Runs: 66, 58, 60, 68, 58 seconds
        ---> Average: 62 seconds
        - Without weights
        ===> Runs: 66, 82, 72, 58, 72 seconds
        ---> Average: 70 seconds
        """
        open_nodes = self.database.get_web3_nodes(blockchain=self.blockchain, only_active=True)  # noqa: E501
        if skip_etherscan:
            selection = [wnode for wnode in open_nodes if wnode.node_info.name != self.etherscan_node_name and wnode.node_info.owned is False]  # noqa: E501
        else:
            selection = [wnode for wnode in open_nodes if wnode.node_info.owned is False]

        ordered_list = []
        while len(selection) != 0:
            weights = []
            for entry in selection:
                weights.append(float(entry.weight))
            node = random.choices(selection, weights, k=1)
            ordered_list.append(node[0])
            selection.remove(node[0])

        owned_nodes = [node for node in self.web3_mapping if node.owned]
        if len(owned_nodes) != 0:
            # Assigning one is just a default since we always use it.
            # The weight is only important for the other nodes since they
            # are selected using this parameter
            ordered_list = [WeightedNode(node_info=node, weight=ONE, active=True) for node in owned_nodes] + ordered_list  # noqa: E501
        return ordered_list

    def get_own_node_web3(self) -> Optional[Web3]:
        for node, web3_instance in self.web3_mapping.items():
            if node.owned:
                return web3_instance
        return None

    def get_own_node_info(self) -> Optional[NodeName]:
        for node in self.web3_mapping:
            if node.owned:
                return node
        return None

    def get_connected_nodes(self) -> List[NodeName]:
        return list(self.web3_mapping.keys())

    def attempt_connect(
            self,
            node: NodeName,
            connectivity_check: bool = True,
    ) -> Tuple[bool, str]:
        """Attempt to connect to a particular node type

        For our own node if the given rpc endpoint is not the same as the saved one
        the connection is re-attempted to the new one
        """
        message = ''
        node_connected = self.web3_mapping.get(node, None) is not None
        if node_connected:
            return True, f'Already connected to {node} {self.chain_name} node'

        try:
            rpc_endpoint = node.endpoint
            parsed_rpc_endpoint = urlparse(node.endpoint)
            if not parsed_rpc_endpoint.scheme:
                rpc_endpoint = f'http://{node.endpoint}'
            provider = HTTPProvider(
                endpoint_uri=node.endpoint,
                request_kwargs={'timeout': self.rpc_timeout},
            )
            ens = ENS(provider)
            web3 = Web3(provider, ens=ens)
        except requests.exceptions.RequestException:
            message = f'Failed to connect to {self.chain_name} node {node} at endpoint {rpc_endpoint}'  # noqa: E501
            log.warning(message)
            return False, message

        try:
            is_connected = web3.isConnected()
        except AssertionError:
            # Terrible, terrible hack but needed due to https://github.com/rotki/rotki/issues/1817
            is_connected = False

        if is_connected:
            # Also make sure we are actually connected to the right network
            synchronized = True
            msg = ''
            try:
                if connectivity_check:
                    try:
                        network_id = int(web3.net.version)
                    except requests.exceptions.RequestException as e:
                        msg = (
                            f'Connected to node {node} at endpoint {rpc_endpoint} but'
                            f'failed to request node version due to {str(e)}'
                        )
                        log.warning(msg)
                        return False, msg

                    if network_id != self.chain_id.value:
                        message = (
                            f'Connected to {self.chain_name} node {node} at endpoint {rpc_endpoint} but '  # noqa: E501
                            f'it is not on the expected network value {self.chain_id.value}. '
                            f'The chain id the node is in is {network_id}.'
                        )
                        log.warning(message)
                        return False, message

                    try:
                        current_block = web3.eth.block_number  # pylint: disable=no-member
                        latest_block = self.query_highest_block()
                    except (requests.exceptions.RequestException, RemoteError) as e:
                        msg = f'Could not query latest block due to {str(e)}'
                        log.warning(msg)
                        synchronized = False
                    else:
                        synchronized, msg = _is_synchronized(current_block, latest_block)
            except ValueError as e:
                message = (
                    f'Failed to connect to {self.chain_name} node {node} at endpoint '
                    f'{rpc_endpoint} due to {str(e)}'
                )
                return False, message

            if not synchronized:
                self.msg_aggregator.add_warning(
                    f'We could not verify that {self.chain_name} node {node} is '
                    'synchronized with the network. Balances and other queries '
                    'may be incorrect.',
                )

            log.info(f'Connected {self.chain_name} node {node} at {rpc_endpoint}')
            self.web3_mapping[node] = web3
            return True, ''

        # else
        message = f'Failed to connect to {self.chain_name} node {node} at endpoint {rpc_endpoint}'
        log.warning(message)
        return False, message

    def connect_to_multiple_nodes(self, nodes: Sequence[WeightedNode]) -> None:
        self.web3_mapping = {}
        for weighted_node in nodes:
            if weighted_node.node_info.name == self.etherscan_node_name:
                continue

            task_name = f'Attempt connection to {str(weighted_node.node_info.name)} {self.chain_name} node'  # noqa: E501
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=self.attempt_connect,
                node=weighted_node.node_info,
                connectivity_check=True,
            )

    def query(self, method: Callable, call_order: Sequence[WeightedNode], **kwargs: Any) -> Any:
        """Queries evm related data by performing a query of the provided method to all given nodes

        The first node in the call order that gets a successful response returns.
        If none get a result then RemoteError is raised
        """
        for weighted_node in call_order:
            node = weighted_node.node_info
            web3 = self.web3_mapping.get(node, None)
            if web3 is None and node.name != self.etherscan_node_name:
                continue

            try:
                result = method(web3, **kwargs)
            except (
                RemoteError,
                requests.exceptions.RequestException,
                BlockchainQueryError,
                TransactionNotFound,
                BlockNotFound,
                BadResponseFormat,
                ValueError,  # Yabir saw this happen with mew node for unavailable method at node. Since it's generic we should replace if web3 implements https://github.com/ethereum/web3.py/issues/2448  # noqa: E501
            ) as e:
                log.warning(f'Failed to query {node} for {str(method)} due to {str(e)}')
                # Catch all possible errors here and just try next node call
                continue

            return result

        # no node in the call order list was succesfully queried
        raise RemoteError(
            f'Failed to query {str(method)} after trying the following '
            f'nodes: {[str(x) for x in call_order]}. Check logs for details.',
        )

    def _get_latest_block_number(self, web3: Optional[Web3]) -> int:
        if web3 is not None:
            return web3.eth.block_number

        # else
        return self.etherscan.get_latest_block_number()

    def get_latest_block_number(self, call_order: Optional[Sequence[WeightedNode]] = None) -> int:
        return self.query(
            method=self._get_latest_block_number,
            call_order=call_order if call_order is not None else self.default_call_order(),
        )

    def get_historical_balance(
            self,
            address: ChecksumEvmAddress,
            block_number: int,
    ) -> Optional[FVal]:
        """Attempts to get a historical eth balance from the local own node only.
        If there is no node or the node can't query historical balance (not archive) then
        returns None"""
        web3 = self.get_own_node_web3()
        if web3 is None:
            return None

        try:
            result = web3.eth.get_balance(address, block_identifier=block_number)
        except (
                requests.exceptions.RequestException,
                BlockchainQueryError,
                KeyError,  # saw this happen inside web3.py if resulting json contains unexpected key. Happened with mycrypto's node  # noqa: E501
        ):
            return None

        try:
            balance = from_wei(FVal(result))
        except ValueError:
            return None

        return balance

    def get_block_by_number(
            self,
            num: int,
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> Dict[str, Any]:
        return self.query(
            method=self._get_block_by_number,
            call_order=call_order if call_order is not None else self.default_call_order(),
            num=num,
        )

    def _get_block_by_number(self, web3: Optional[Web3], num: int) -> Dict[str, Any]:
        """Returns the block object corresponding to the given block number

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
        there is a problem with its query.
        - BlockNotFound if number used to lookup the block can't be found. Raised
        by web3.eth.get_block().
        """
        if web3 is None:
            return self.etherscan.get_block_by_number(num)

        block_data: MutableAttributeDict = MutableAttributeDict(web3.eth.get_block(num))  # type: ignore # pylint: disable=no-member  # noqa: E501
        block_data['hash'] = hex_or_bytes_to_str(block_data['hash'])
        return dict(block_data)

    def get_code(
            self,
            account: ChecksumEvmAddress,
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> str:
        return self.query(
            method=self._get_code,
            call_order=call_order if call_order is not None else self.default_call_order(),
            account=account,
        )

    def _get_code(self, web3: Optional[Web3], account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        """
        if web3 is None:
            return self.etherscan.get_code(account)

        return hex_or_bytes_to_str(web3.eth.getCode(account))

    def _call_contract_etherscan(
            self,
            contract_address: ChecksumEvmAddress,
            abi: List,
            method_name: str,
            arguments: Optional[List[Any]] = None,
    ) -> Any:
        """Performs an eth_call to an evm contract via etherscan

        May raise:
        - RemoteError if there is a problem with
        reaching etherscan or with the returned result
        """
        web3 = Web3()
        contract = web3.eth.contract(address=contract_address, abi=abi)
        input_data = contract.encodeABI(method_name, args=arguments if arguments else [])
        result = self.etherscan.eth_call(
            to_address=contract_address,
            input_data=input_data,
        )
        if result == '0x':
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address} for {method_name} '
                f'and chain {self.chain_name} with arguments: {str(arguments)} '
                f'via etherscan. Returned 0x result',
            )

        fn_abi = contract._find_matching_fn_abi(
            fn_identifier=method_name,
            args=arguments,
        )
        output_types = get_abi_output_types(fn_abi)
        output_data = web3.codec.decode_abi(output_types, bytes.fromhex(result[2:]))

        if len(output_data) == 1:
            # due to https://github.com/PyCQA/pylint/issues/4114
            return output_data[0]  # pylint: disable=unsubscriptable-object
        return output_data

    def _get_transaction_receipt(
            self,
            web3: Optional[Web3],
            tx_hash: EVMTxHash,
    ) -> Dict[str, Any]:
        if web3 is None:
            tx_receipt = self.etherscan.get_transaction_receipt(tx_hash)
            try:
                # Turn hex numbers to int
                block_number = int(tx_receipt['blockNumber'], 16)
                tx_receipt['blockNumber'] = block_number
                tx_receipt['cumulativeGasUsed'] = int(tx_receipt['cumulativeGasUsed'], 16)
                tx_receipt['gasUsed'] = int(tx_receipt['gasUsed'], 16)
                tx_receipt['status'] = int(tx_receipt.get('status', '0x1'), 16)
                tx_index = int(tx_receipt['transactionIndex'], 16)
                tx_receipt['transactionIndex'] = tx_index
                for receipt_log in tx_receipt['logs']:
                    receipt_log['blockNumber'] = block_number
                    receipt_log['logIndex'] = deserialize_int_from_hex(
                        symbol=receipt_log['logIndex'],
                        location='etherscan tx receipt',
                    )
                    receipt_log['transactionIndex'] = tx_index
            except (DeserializationError, ValueError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'missing key {msg}'
                log.error(
                    f'Couldnt deserialize transaction receipt {tx_receipt} data from '
                    f'etherscan due to {msg}',
                )
                raise RemoteError(
                    f'Couldnt deserialize transaction receipt data from etherscan '
                    f'due to {msg}. Check logs for details',
                ) from e
            return tx_receipt

        # Can raise TransactionNotFound if the user's node is pruned and transaction is old
        tx_receipt = web3.eth.get_transaction_receipt(tx_hash)  # type: ignore
        return process_result(tx_receipt)

    def get_transaction_receipt(
            self,
            tx_hash: EVMTxHash,
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> Dict[str, Any]:
        return self.query(
            method=self._get_transaction_receipt,
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
        )

    def _get_transaction_by_hash(
            self,
            web3: Optional[Web3],
            tx_hash: EVMTxHash,
    ) -> EvmTransaction:
        if web3 is None:
            tx_data = self.etherscan.get_transaction_by_hash(tx_hash=tx_hash)
        else:
            tx_data = web3.eth.get_transaction(tx_hash)  # type: ignore

        try:
            transaction = deserialize_evm_transaction(data=tx_data, internal=False, manager=self)  # noqa: E501
        except (DeserializationError, ValueError) as e:
            raise RemoteError(
                f'Couldnt deserialize evm transaction data from {tx_data}. Error: {str(e)}',
            ) from e

        return transaction

    def get_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> EvmTransaction:
        return self.query(
            method=self._get_transaction_by_hash,
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
        )

    def call_contract(
            self,
            contract_address: ChecksumEvmAddress,
            abi: List,
            method_name: str,
            arguments: Optional[List[Any]] = None,
            call_order: Optional[Sequence[WeightedNode]] = None,
            block_identifier: BlockIdentifier = 'latest',
    ) -> Any:
        return self.query(
            method=self._call_contract,
            call_order=call_order if call_order is not None else self.default_call_order(),
            contract_address=contract_address,
            abi=abi,
            method_name=method_name,
            arguments=arguments,
            block_identifier=block_identifier,
        )

    def _call_contract(
            self,
            web3: Optional[Web3],
            contract_address: ChecksumEvmAddress,
            abi: List,
            method_name: str,
            arguments: Optional[List[Any]] = None,
            block_identifier: BlockIdentifier = 'latest',
    ) -> Any:
        """Performs an eth_call to an evm contract

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        - BlockchainQueryError if web3 is used and there is a VM execution error
        """
        if web3 is None:
            return self._call_contract_etherscan(
                contract_address=contract_address,
                abi=abi,
                method_name=method_name,
                arguments=arguments,
            )

        contract = web3.eth.contract(address=contract_address, abi=abi)
        try:
            method = getattr(contract.caller(block_identifier=block_identifier), method_name)
            result = method(*arguments if arguments else [])
        except (ValueError, BadFunctionCallOutput) as e:
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address}: {str(e)}',
            ) from e
        return result

    def get_logs(
            self,
            contract_address: ChecksumEvmAddress,
            abi: List,
            event_name: str,
            argument_filters: Dict[str, Any],
            from_block: int,
            to_block: Union[int, Literal['latest']] = 'latest',
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> List[Dict[str, Any]]:
        if call_order is None:  # Default call order for logs
            call_order = [self.etherscan_node]
            if (node_info := self.get_own_node_info()) is not None:
                call_order.append(
                    WeightedNode(
                        node_info=node_info,
                        active=True,
                        weight=ONE,
                    ),
                )
        return self.query(
            method=self._get_logs,
            call_order=call_order,
            contract_address=contract_address,
            abi=abi,
            event_name=event_name,
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )

    def _get_logs(
            self,
            web3: Optional[Web3],
            contract_address: ChecksumEvmAddress,
            abi: List,
            event_name: str,
            argument_filters: Dict[str, Any],
            from_block: int,
            to_block: Union[int, Literal['latest']] = 'latest',
    ) -> List[Dict[str, Any]]:
        """Queries logs of an evm contract
        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        """
        event_abi = find_matching_event_abi(abi=abi, event_name=event_name)
        _, filter_args = construct_event_filter_params(
            event_abi=event_abi,
            abi_codec=Web3().codec,
            contract_address=contract_address,
            argument_filters=argument_filters,
            fromBlock=from_block,
            toBlock=to_block,
        )
        if event_abi['anonymous']:
            # web3.py does not handle the anonymous events correctly and adds the first topic
            filter_args['topics'] = filter_args['topics'][1:]
        events: List[Dict[str, Any]] = []
        start_block = from_block
        if web3 is not None:
            events = _query_web3_get_logs(
                web3=web3,
                filter_args=filter_args,
                from_block=from_block,
                to_block=to_block,
                contract_address=contract_address,
                event_name=event_name,
                argument_filters=argument_filters,
                initial_block_range=self.logquery_block_range(web3=web3, contract_address=contract_address),  # noqa: E501
            )
        else:  # etherscan
            until_block = (
                self.etherscan.get_latest_block_number() if to_block == 'latest' else to_block
            )
            blocks_step = 300000
            while start_block <= until_block:
                while True:  # loop to continuously reduce block range if need b
                    end_block = min(start_block + blocks_step, until_block)
                    try:
                        new_events = self.etherscan.get_logs(
                            contract_address=contract_address,
                            topics=filter_args['topics'],  # type: ignore
                            from_block=start_block,
                            to_block=end_block,
                        )
                    except RemoteError as e:
                        if 'Please select a smaller result dataset' in str(e):

                            blocks_step = blocks_step // 2
                            if blocks_step < 100:
                                raise  # stop trying
                            # else try with the smaller step
                            continue

                        # else some other error
                        raise

                    break  # we must have a result

                # Turn all Hex ints to ints
                for e_idx, event in enumerate(new_events):
                    try:
                        block_number = deserialize_int_from_hex(
                            symbol=event['blockNumber'],
                            location='etherscan log query',
                        )
                        log_index = deserialize_int_from_hex(
                            symbol=event['logIndex'],
                            location='etherscan log query',
                        )
                        # Try to see if the event is a duplicate that got returned
                        # in the previous iteration
                        for previous_event in reversed(events):
                            if previous_event['blockNumber'] < block_number:
                                break

                            same_event = (
                                previous_event['logIndex'] == log_index and
                                previous_event['transactionHash'] == event['transactionHash']
                            )
                            if same_event:
                                events.pop()

                        new_events[e_idx]['address'] = deserialize_evm_address(
                            event['address'],
                        )
                        new_events[e_idx]['blockNumber'] = block_number
                        new_events[e_idx]['timeStamp'] = deserialize_int_from_hex(
                            symbol=event['timeStamp'],
                            location='etherscan log query',
                        )
                        new_events[e_idx]['gasPrice'] = deserialize_int_from_hex(
                            symbol=event['gasPrice'],
                            location='etherscan log query',
                        )
                        new_events[e_idx]['gasUsed'] = deserialize_int_from_hex(
                            symbol=event['gasUsed'],
                            location='etherscan log query',
                        )
                        new_events[e_idx]['logIndex'] = log_index
                        new_events[e_idx]['transactionIndex'] = deserialize_int_from_hex(
                            symbol=event['transactionIndex'],
                            location='etherscan log query',
                        )
                    except DeserializationError as e:
                        raise RemoteError(
                            'Couldnt decode an etherscan event due to {str(e)}}',
                        ) from e

                # etherscan will only return 1000 events in one go. If more than 1000
                # are returned such as when no filter args are provided then continue
                # the query from the last block
                if len(new_events) == 1000:
                    start_block = new_events[-1]['blockNumber']
                else:
                    start_block = end_block + 1
                events.extend(new_events)

        return events

    def get_event_timestamp(self, event: Dict[str, Any]) -> Timestamp:
        """Reads an event returned either by etherscan or web3 and gets its timestamp

        Etherscan events contain a timestamp. Normal web3 events don't so it needs to
        be queried from the block number

        We could also add this to the get_logs() call but would add unnecessary
        rpc calls for get_block_by_number() for each log entry. Better have it
        lazy queried like this.

        TODO: Perhaps better approach would be a log event class for this
        """
        if 'timeStamp' in event:
            # event from etherscan
            return Timestamp(event['timeStamp'])

        # event from web3
        block_number = event['blockNumber']
        block_data = self.get_block_by_number(block_number)
        return Timestamp(block_data['timestamp'])

    def multicall(
            self,
            calls: List[Tuple[ChecksumEvmAddress, str]],
            # only here to comply with multicall_2
            require_success: bool = True,  # pylint: disable=unused-argument
            call_order: Optional[Sequence['WeightedNode']] = None,
            block_identifier: BlockIdentifier = 'latest',
            calls_chunk_size: int = MULTICALL_CHUNKS,
    ) -> Any:
        """Uses MULTICALL contract. Failure of one call is a failure of the entire multicall.
        source: https://etherscan.io/address/0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441#code"""
        calls_chunked = list(get_chunks(calls, n=calls_chunk_size))
        output = []
        for call_chunk in calls_chunked:
            multicall_result = self.contract_multicall.call(
                manager=self,
                method_name='aggregate',
                arguments=[call_chunk],
                call_order=call_order,
                block_identifier=block_identifier,
            )
            _, chunk_output = multicall_result
            output += chunk_output
        return output

    def multicall_2(
            self,
            calls: List[Tuple[ChecksumEvmAddress, str]],
            require_success: bool,
            call_order: Optional[Sequence['WeightedNode']] = None,
            block_identifier: BlockIdentifier = 'latest',
            # only here to comply with multicall
            calls_chunk_size: int = MULTICALL_CHUNKS,  # pylint: disable=unused-argument
    ) -> List[Tuple[bool, bytes]]:
        """
        Uses MULTICALL_2 contract. If require success is set to False any call in the list
        of calls is allowed to fail.
        source: https://etherscan.io/address/0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696#code"""
        return self.contract_multicall_2.call(
            manager=self,
            method_name='tryAggregate',
            arguments=[require_success, calls],
            call_order=call_order,
            block_identifier=block_identifier,
        )

    def multicall_specific(
            self,
            contract: 'EvmContract',
            method_name: str,
            arguments: List[Any],
            call_order: Optional[Sequence['WeightedNode']] = None,
            decode_result: bool = True,
    ) -> Any:
        calls = [(
            contract.address,
            contract.encode(method_name=method_name, arguments=i),
        ) for i in arguments]
        output = self.multicall(calls, True, call_order)
        if decode_result is False:
            return output
        return [contract.decode(x, method_name, arguments[0]) for x in output]

    def get_erc20_contract_info(self, address: ChecksumEvmAddress) -> Dict[str, Any]:
        """
        Query an erc20 contract address and return basic information as:
        - Decimals
        - name
        - symbol
        At all times, the dictionary returned contains the keys; decimals, name & symbol.
        Although the values might be None.
        if it is provided in the contract. This method may raise:
        - BadFunctionCallOutput: If there is an error calling a bad address
        """
        cache = self.contract_info_cache.get(address)
        if cache is not None:
            return cache

        properties = ('decimals', 'symbol', 'name')
        info: Dict[str, Any] = {}

        contract = EvmContract(address=address, abi=ERC20TOKEN_ABI, deployed_block=0)
        try:
            # Output contains call status and result
            output = self.multicall_2(
                require_success=False,
                calls=[(address, contract.encode(method_name=prop)) for prop in properties],
            )
        except RemoteError:
            # If something happens in the connection the output should have
            # the same length as the tuple of properties
            output = [(False, b'')] * len(properties)
        try:
            decoded = self._process_contract_info(
                output=output,
                properties=properties,
                contract=contract,
                token_kind=EvmTokenKind.ERC20,
            )
        except (OverflowError, InsufficientDataBytes) as e:
            # This can happen when contract follows the ERC20 standard methods
            # but name and symbol return bytes instead of string. UNIV1 LP is such a case
            # It can also happen if the method is missing and they are all hitting
            # the fallback function. old WETH contract is such a case
            log.error(
                f'{address} failed to decode as ERC20 token. '
                f'Trying with token ABI using bytes. {str(e)}',
            )
            contract = EvmContract(address=address, abi=UNIV1_LP_ABI, deployed_block=0)
            decoded = self._process_contract_info(
                output=output,
                properties=properties,
                contract=contract,
                token_kind=EvmTokenKind.ERC20,
            )
            log.debug(f'{address} was succesfuly decoded as ERC20 token')

        for prop, value in zip(properties, decoded):
            if isinstance(value, bytes):
                value = value.rstrip(b'\x00').decode()
            info[prop] = value

        self.contract_info_cache[address] = info
        return info

    def get_erc721_contract_info(self, address: ChecksumEvmAddress) -> Dict[str, Any]:
        """
        Query an erc721 contract address and return basic information.
        - name
        - symbol
        At all times, the dictionary returned contains the keys; name & symbol.
        Although the values might be None. https://eips.ethereum.org/EIPS/eip-721
        According to the standard both name and symbol are optional.
        if it is provided in the contract. This method may raise:
        - BadFunctionCallOutput: If there is an error calling a bad address
        - NotERC721Conformant: If the address can't be decoded as an ERC721 contract
        """
        cache = self.contract_info_cache.get(address)
        if cache is not None:
            return cache

        properties = ('symbol', 'name')
        info: Dict[str, Any] = {}

        contract = EvmContract(address=address, abi=ERC721TOKEN_ABI, deployed_block=0)
        try:
            # Output contains call status and result
            output = self.multicall_2(
                require_success=False,
                calls=[(address, contract.encode(method_name=prop)) for prop in properties],
            )
        except RemoteError:
            # If something happens in the connection the output should have
            # the same length as the tuple of properties
            output = [(False, b'')] * len(properties)
        try:
            decoded = self._process_contract_info(
                output=output,
                properties=properties,
                contract=contract,
                token_kind=EvmTokenKind.ERC721,
            )
        except (OverflowError, InsufficientDataBytes) as e:
            raise NotERC721Conformant(f'{address} token does not conform to the ERC721 spec') from e  # noqa: E501

        for prop, value in zip(properties, decoded):
            if isinstance(value, bytes):
                value = value.rstrip(b'\x00').decode()
            info[prop] = value

        self.contract_info_cache[address] = info
        return info

    def _process_contract_info(
            self,
            output: List[Tuple[bool, bytes]],
            properties: Tuple[str, ...],
            contract: EvmContract,
            token_kind: EvmTokenKind,
    ) -> List[Optional[Union[int, str, bytes]]]:
        """Decodes information i.e. (decimals, symbol, name) about the token contract.
        - `decimals` property defaults to 18.
        - `name` and `symbol` default to None.
        May raise:
        - OverflowError
        - InsufficientDataBytes
        """
        decoded_contract_info = []
        for method_name, method_value in zip(properties, output):
            if method_value[0] is True and len(method_value[1]) != 0:
                decoded_contract_info.append(contract.decode(method_value[1], method_name)[0])
                continue

            if token_kind == EvmTokenKind.ERC20:
                # for missing erc20 methods, use default decimals for decimals or None for others
                if method_name == 'decimals':
                    decoded_contract_info.append(DEFAULT_TOKEN_DECIMALS)
                else:
                    decoded_contract_info.append(None)
            else:  # for all others default to None
                decoded_contract_info.append(None)

        return decoded_contract_info

    @abstractmethod
    def query_highest_block(self) -> BlockNumber:
        """
        Attempts to query an external service for the block height

        Returns the highest blockNumber

        May Raise RemoteError if querying fails
        """
        ...

    @abstractmethod
    def have_archive(self, requery: bool = False) -> bool:
        """
        Checks to see if our own connected node is an archive node

        If requery is True it always queries the node. Otherwise it remembers last query.
        """
        ...

    @abstractmethod
    def get_blocknumber_by_time(self, ts: Timestamp, etherscan: bool = True) -> int:
        """Searches for the blocknumber of a specific timestamp"""
        ...

    def logquery_block_range(
            self,
            web3: Web3,  # pylint: disable=unused-argument
            contract_address: ChecksumEvmAddress,  # pylint: disable=unused-argument
    ) -> int:
        """
        May be optionally implemented by subclasses to set special rules on how to
        decide the block range for a specific logquery.
        """
        return WEB3_LOGQUERY_BLOCK_RANGE
