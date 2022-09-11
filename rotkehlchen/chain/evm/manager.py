import logging
import random
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests
from ens import ENS
from eth_typing import BlockNumber
from web3 import HTTPProvider, Web3
from web3.datastructures import MutableAttributeDict
from web3.exceptions import BadResponseFormat, BlockNotFound, TransactionNotFound

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.types import ETHERSCAN_NODE_NAME, NodeName, WeightedNode
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int_from_hex
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    SUPPORTED_BLOCKCHAIN_TO_CHAINID,
    ChecksumEvmAddress,
    EVMTxHash,
    SupportedBlockchain,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_str
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn
from rotkehlchen.utils.network import request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _is_synchronized(current_block: int, latest_block: int) -> Tuple[bool, str]:
    """ Validate that the ethereum node is synchronized
            within 20 blocks of latest block

        Returns a tuple (results, message)
            - result: Boolean for confirmation of synchronized
            - message: A message containing information on what the status is.
    """
    message = ''
    if current_block < (latest_block - 20):
        message = (
            f'Found ethereum node but it is out of sync. {current_block} / '
            f'{latest_block}. Will use etherscan.'
        )
        log.warning(message)
        return False, message

    return True, message


class EvmManager(LockableQueryMixIn):
    """EvmManager defines a basic implementation for most of EVM chains."""
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

        self.blocks_subgraph = Graph(
            'https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks',
        )

        # Note: you might need to redefine this one in the child class
        self.contract_info_cache: Dict[ChecksumEvmAddress, Dict[str, Any]] = {}

    def query_eth_highest_block(self) -> BlockNumber:
        """ Attempts to query an external service for the block height

        Returns the highest blockNumber

        May Raise RemoteError if querying fails
        """

        url = 'https://api.blockcypher.com/v1/eth/main'
        log.debug('Querying blockcypher for ETH highest block', url=url)
        eth_resp: Optional[Dict[str, str]]
        try:
            eth_resp = request_get_dict(url)
        except (RemoteError, UnableToDecryptRemoteData, requests.exceptions.RequestException):
            eth_resp = None

        block_number: Optional[int]
        if eth_resp and 'height' in eth_resp:
            block_number = int(eth_resp['height'])
            log.debug('ETH highest block result', block=block_number)
        else:
            block_number = self.etherscan.get_latest_block_number()
            log.debug('ETH highest block result', block=block_number)

        return BlockNumber(block_number)

    def attempt_connect(
            self,
            node: NodeName,
            mainnet_check: bool = True,
    ) -> Tuple[bool, str]:
        """Attempt to connect to a particular node type

        For our own node if the given rpc endpoint is not the same as the saved one
        the connection is re-attempted to the new one
        """
        message = ''
        node_connected = self.web3_mapping.get(node, None) is not None
        if node_connected:
            return True, f'Already connected to {node} ethereum node'

        try:
            ethrpc_endpoint = node.endpoint
            parsed_eth_rpc_endpoint = urlparse(node.endpoint)
            if not parsed_eth_rpc_endpoint.scheme:
                ethrpc_endpoint = f'http://{node.endpoint}'
            provider = HTTPProvider(
                endpoint_uri=node.endpoint,
                request_kwargs={'timeout': self.rpc_timeout},
            )
            ens = ENS(provider)
            web3 = Web3(provider, ens=ens)
        except requests.exceptions.RequestException:
            message = f'Failed to connect to ethereum node {node} at endpoint {ethrpc_endpoint}'
            log.warning(message)
            return False, message

        try:
            is_connected = web3.isConnected()
        except AssertionError:
            # Terrible, terrible hack but needed due to https://github.com/rotki/rotki/issues/1817
            is_connected = False

        if is_connected:
            # Also make sure we are actually connected to the Ethereum mainnet
            synchronized = True
            msg = ''
            try:
                if mainnet_check:
                    try:
                        network_id = int(web3.net.version)
                    except requests.exceptions.RequestException as e:
                        msg = (
                            f'Connected to node {node} at endpoint {ethrpc_endpoint} but'
                            f'failed to request node version due to {str(e)}'
                        )
                        log.warning(msg)
                        return False, msg

                    if network_id != 1:
                        message = (
                            f'Connected to ethereum node {node} at endpoint {ethrpc_endpoint} but '
                            f'it is not on the ethereum mainnet. The chain id '
                            f'the node is in is {network_id}.'
                        )
                        log.warning(message)
                        return False, message

                    try:
                        current_block = web3.eth.block_number  # pylint: disable=no-member
                        latest_block = self.query_eth_highest_block()
                    except (requests.exceptions.RequestException, RemoteError) as e:
                        msg = f'Could not query latest block due to {str(e)}'
                        log.warning(msg)
                        synchronized = False
                    else:
                        synchronized, msg = _is_synchronized(current_block, latest_block)
            except ValueError as e:
                message = (
                    f'Failed to connect to ethereum node {node} at endpoint '
                    f'{ethrpc_endpoint} due to {str(e)}'
                )
                return False, message

            if not synchronized:
                self.msg_aggregator.add_warning(
                    f'We could not verify that ethereum node {node} is '
                    'synchronized with the ethereum mainnet. Balances and other queries '
                    'may be incorrect.',
                )

            log.info(f'Connected ethereum node {node} at {ethrpc_endpoint}')
            self.web3_mapping[node] = web3
            return True, ''

        # else
        message = f'Failed to connect to ethereum node {node} at endpoint {ethrpc_endpoint}'
        log.warning(message)
        return False, message

    def query(self, method: Callable, call_order: Sequence[WeightedNode], **kwargs: Any) -> Any:
        """
        Queries ethereum related data by performing the provided method to all given nodes

        The first node in the call order that gets a succcesful response returns.
        If none get a result then a remote error is raised.
        May raise:
        - RemoteError
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

    def connect_to_multiple_nodes(self, nodes: Sequence[WeightedNode]) -> None:
        self.web3_mapping = {}
        for weighted_node in nodes:
            if weighted_node.node_info.name == self.etherscan_node_name:
                continue

            task_name = f'Attempt connection to {str(weighted_node.node_info.name)} ethereum node'
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=self.attempt_connect,
                node=weighted_node.node_info,
                mainnet_check=True,
            )

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

    def default_call_order(self, skip_etherscan: bool = False) -> List[WeightedNode]:
        """Default call order for ethereum nodes

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
            selection = [wnode for wnode in open_nodes if wnode.node_info.name != ETHERSCAN_NODE_NAME and wnode.node_info.owned is False]  # noqa: E501
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
