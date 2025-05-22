import json
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Sequence
from contextlib import suppress
from itertools import zip_longest
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

import requests
from ens import ENS
from eth_abi.exceptions import DecodingError
from eth_typing.abi import ABI
from eth_utils.abi import get_abi_output_types
from requests import RequestException
from web3 import HTTPProvider, Web3
from web3._utils.contracts import find_matching_event_abi
from web3._utils.filters import construct_event_filter_params
from web3.datastructures import MutableAttributeDict
from web3.exceptions import InvalidAddress, TransactionNotFound, Web3Exception
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import BlockIdentifier, FilterParams

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import (
    ETHEREUM_ETHERSCAN_NODE,
    ETHEREUM_ETHERSCAN_NODE_NAME,
)
from rotkehlchen.chain.ethereum.types import LogIterationCallback
from rotkehlchen.chain.ethereum.utils import MULTICALL_CHUNKS, should_update_protocol_cache
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    ERC20_PROPERTIES,
    ERC20_PROPERTIES_NUM,
    ERC721_PROPERTIES,
    FAKE_GENESIS_TX_RECEIPT,
    GENESIS_HASH,
)
from rotkehlchen.chain.evm.contracts import EvmContract, EvmContracts
from rotkehlchen.chain.evm.proxies_inquirer import EvmProxiesInquirer
from rotkehlchen.chain.evm.types import NodeName, RemoteDataQueryStatus, Web3Node, WeightedNode
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import (
    BlockchainQueryError,
    EventNotInABI,
    NotERC721Conformant,
    RemoteError,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_evm_transaction,
    deserialize_int_from_hex,
)
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    EvmTransaction,
    EVMTxHash,
    Timestamp,
)
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.misc import from_wei, get_chunks
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.transactions import GnosisWithdrawalsQueryParameters
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _connect_task_prefix(chain_name: str) -> str:
    """Helper function to create the connection task greenlet name"""
    return f'Attempt connection to {chain_name} node'


WEB3_LOGQUERY_BLOCK_RANGE = 250000
MAX_NODE_LOG_QUERY_CALLS = 500  # max queries for a node that can query logs from up to 1000/10_000 blocks  # noqa: E501


def _query_web3_get_logs(
        web3: Web3,
        filter_args: FilterParams,
        from_block: int,
        to_block: int | Literal['latest'],
        contract_address: ChecksumEvmAddress,
        event_name: str,
        argument_filters: dict[str, Any],
        initial_block_range: int,
        log_iteration_cb: LogIterationCallback | None = None,
        log_iteration_cb_arguments: 'GnosisWithdrawalsQueryParameters | None' = None,
) -> list[dict[str, Any]]:
    until_block = web3.eth.block_number if to_block == 'latest' else to_block
    events: list[dict[str, Any]] = []
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
            new_events_web3: list[dict[str, Any]] = [dict(x) for x in web3.eth.get_logs(filter_args)]  # noqa: E501
        except (Web3Exception, ValueError, KeyError) as e:
            if isinstance(e, ValueError | Web3Exception):
                try:
                    decoded_error = json.loads(str(e).replace("'", '"'))
                except json.JSONDecodeError:
                    # reraise the value error if the error is not json
                    raise e from None

                msg = decoded_error.get('message', '')
            else:  # temporary hack for key error seen from pokt
                msg = 'query returned more than 10000 results'

            # errors from: https://infura.io/docs/ethereum/json-rpc/eth-getLogs
            if msg == 'query returned more than 10000 results':
                if (until_block - start_block) // 10_000 > MAX_NODE_LOG_QUERY_CALLS:
                    log.debug(f'Querying logs with a range of 10_000 from {web3} will take too much time. Stopping here')  # noqa: E501
                    raise

                block_range = initial_block_range = 9999  # ensure that block range doesn't get reset to a range bigger than what is allowed for this node  # noqa: E501
                continue
            elif msg == 'eth_getLogs is limited to a 1000 blocks range':  # seen in https://1rpc.io/gnosis  # noqa: E501
                if (until_block - start_block) // 1_000 > MAX_NODE_LOG_QUERY_CALLS:
                    log.debug(f'Querying logs with a range of 1000 from {web3} will take too much time. Stopping here')  # noqa: E501
                    raise

                block_range = initial_block_range = 999
                continue
            elif msg == 'query timeout exceeded':
                block_range //= 2
                if block_range < 50:
                    raise  # stop retrying if block range gets too small
                # repeat the query with smaller block range
                continue
            else:  # else, well we tried .. reraise the error
                raise

        # Turn all HexBytes into hex strings
        for e_idx, event in enumerate(new_events_web3):
            new_events_web3[e_idx]['blockHash'] = event['blockHash'].to_0x_hex()
            new_events_web3[e_idx]['data'] = event['data'].to_0x_hex()
            new_topics = [topic.to_0x_hex() for topic in event['topics']]
            new_events_web3[e_idx]['topics'] = new_topics
            new_events_web3[e_idx]['transactionHash'] = event['transactionHash'].to_0x_hex()

        if log_iteration_cb is not None:
            log_iteration_cb(
                last_block_queried=end_block,
                filters=argument_filters,
                new_events=new_events_web3,
                cb_arguments=log_iteration_cb_arguments,
            )

        start_block = end_block + 1
        events.extend(new_events_web3)
        # end of the loop, end of 1 query. Reset the block range to max
        block_range = initial_block_range

    return events


class EvmNodeInquirer(ABC, LockableQueryMixIn):
    """Class containing generic functionality for querying evm nodes

    The child class must implement the following methods:
    - _have_archive
    - _is_pruned
    - get_blocknumber_by_time

    The child class may optionally implement the following:
    - logquery_block_range
    """
    methods_that_query_past_data = (
        '_get_transaction_receipt',
        '_get_transaction_by_hash',
        '_get_logs',
    )

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: Etherscan,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            contracts: EvmContracts,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            native_token: CryptoAsset,
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
            blockscout: Blockscout | None = None,
    ) -> None:
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.blockchain = blockchain
        self.etherscan = etherscan
        self.etherscan_node = ETHEREUM_ETHERSCAN_NODE
        self.contracts = contracts
        self.web3_mapping: dict[NodeName, Web3Node] = {}
        self.rpc_timeout = rpc_timeout
        self.chain_id: SUPPORTED_CHAIN_IDS = blockchain.to_chain_id()
        self.chain_name = self.chain_id.to_name()
        self.native_token = native_token
        # BalanceScanner from mycrypto: https://github.com/MyCryptoHQ/eth-scan
        self.contract_scan = contract_scan
        # Multicall from MakerDAO: https://github.com/makerdao/multicall/
        self.contract_multicall = contract_multicall
        self.blockscout = blockscout
        # keep a cache per chain id of timestamp to block to avoid querying multiple times
        # the same information. Remove from here with
        # https://github.com/rotki/rotki/issues/9998
        self.timestamp_to_block_cache: dict[ChainID, LRUCacheWithRemove[Timestamp, int]] = defaultdict(lambda: LRUCacheWithRemove(maxsize=32))  # noqa: E501

        # A cache for erc20 and erc721 contract info to not requery the info
        self.contract_info_erc20_cache: LRUCacheWithRemove[ChecksumEvmAddress, dict[str, Any]] = LRUCacheWithRemove(maxsize=1024)  # noqa: E501
        self.contract_info_erc721_cache: LRUCacheWithRemove[ChecksumEvmAddress, dict[str, Any]] = LRUCacheWithRemove(maxsize=512)  # noqa: E501
        # failed_to_connect_nodes keeps the nodes that we couldn't connect while
        # doing remote queries so they aren't tried again if they get chosen. At the
        # moment of writing this we don't remove entries from the set after some time.
        # To force the app to retry a node a restart is needed.
        self.failed_to_connect_nodes: set[str] = set()
        LockableQueryMixIn.__init__(self)
        # Log the available nodes so we have extra information when debugging connection errors.
        nodes = '\n'.join([str(x.serialize()) for x in self.default_call_order()])  # variable because \ is not valid in f-strings  # noqa: E501
        log.debug(f'RPC nodes at startup {nodes}')

    def maybe_connect_to_nodes(self, when_tracked_accounts: bool) -> None:
        """Start async connect to the saved nodes for the given evm chain if needed.

        If `when_tracked_accounts` is True then it will connect when we have some
        tracked accounts in the DB. Otherwise when we have none.

        In ethereum case always connect to nodes. Needed for ENS resolution.
        For other EVM chains we respect `when_tracked_accounts`.
        """
        if self.connected_to_any_web3() or self.greenlet_manager.has_task(_connect_task_prefix(self.chain_name)):  # noqa: E501
            return

        with self.database.conn.read_ctx() as cursor:
            accounts = self.database.get_blockchain_accounts(cursor)

        tracked_accounts_num = len(accounts.get(self.blockchain))
        if (
            (tracked_accounts_num != 0 and when_tracked_accounts) or
            (tracked_accounts_num == 0 and (when_tracked_accounts is False or self.chain_id == ChainID.ETHEREUM))  # noqa: E501
        ):
            rpc_nodes = self.database.get_rpc_nodes(blockchain=self.blockchain, only_active=True)
            self.connect_to_multiple_nodes(rpc_nodes)

    def connected_to_any_web3(self) -> bool:
        return len(self.web3_mapping) != 0

    def get_own_node_web3(self) -> Web3 | None:
        for node, web3node in self.web3_mapping.items():
            if node.owned:
                return web3node.web3_instance
        return None

    def get_own_node_info(self) -> NodeName | None:
        for node in self.web3_mapping:
            if node.owned:
                return node
        return None

    def get_connected_nodes(self) -> list[NodeName]:
        return list(self.web3_mapping.keys())

    def default_call_order(self, skip_etherscan: bool = False) -> list[WeightedNode]:
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
        open_nodes = self.database.get_rpc_nodes(blockchain=self.blockchain, only_active=True)
        selection = [wnode for wnode in open_nodes if wnode.node_info.owned is False]
        ordered_list = []
        while len(selection) != 0:
            weights = [float(entry.weight) for entry in selection]
            node = random.choices(selection, weights, k=1)
            ordered_list.append(node[0])
            selection.remove(node[0])

        if not skip_etherscan:  # explicitly adding at the end to minimize etherscan API queries
            ordered_list.append(self.etherscan_node)

        owned_nodes = [node.node_info for node in open_nodes if node.node_info.owned]
        if len(owned_nodes) != 0:
            # Assigning one is just a default since we always use it.
            # The weight is only important for the other nodes since they
            # are selected using this parameter
            ordered_list = [WeightedNode(node_info=node, weight=ONE, active=True) for node in owned_nodes] + ordered_list  # noqa: E501
        return ordered_list

    def get_multi_balance(
            self,
            accounts: Sequence[ChecksumEvmAddress],
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[ChecksumEvmAddress, FVal]:
        """Returns a dict with keys being accounts and balances in the chain native token.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        balances: dict[ChecksumEvmAddress, FVal] = {}
        if len(accounts) == 0:
            return balances

        log.debug(
            f'Querying {self.chain_name} chain for {self.blockchain.serialize()} balance',
            eth_addresses=accounts,
        )
        result = self.contract_scan.call(
            node_inquirer=self,
            method_name='ether_balances',
            arguments=[accounts],
            call_order=call_order if call_order is not None else self.default_call_order(),
        )
        balances = {}
        for idx, account in enumerate(accounts):
            balances[account] = from_wei(result[idx])
        return balances

    def get_historical_balance(
            self,
            address: ChecksumEvmAddress,
            block_number: int,
            web3: Web3 | None = None,
    ) -> FVal | None:
        """Attempts to get the historical eth balance using the node provided.

        If `web3` is None, it uses the local own node.
        Returns None if there is no local node or node cannot query historical balance.
        """
        web3 = web3 if web3 is not None else self.get_own_node_web3()
        if web3 is None:
            return None

        try:
            result = web3.eth.get_balance(address, block_identifier=block_number)
        except (
                requests.exceptions.RequestException,
                BlockchainQueryError,
                KeyError,  # saw this happen inside web3.py if resulting json contains unexpected key. Happened with mycrypto's node  # noqa: E501
                Web3Exception,
                ValueError,  # can still happen in web3py v6 for missing trieerror. Essentially historical balance call  # noqa: E501
        ):
            return None

        try:
            balance = from_wei(FVal(result))
        except ValueError:
            return None

        return balance

    def _init_web3(self, node: NodeName) -> tuple[Web3, str]:
        """Initialize a new Web3 object based on a given endpoint"""
        rpc_endpoint = node.endpoint
        parsed_rpc_endpoint = urlparse(node.endpoint)
        if not parsed_rpc_endpoint.scheme:
            rpc_endpoint = f'http://{node.endpoint}'
        provider = HTTPProvider(
            endpoint_uri=node.endpoint,
            request_kwargs={'timeout': self.rpc_timeout},
        )
        ens = ENS(provider) if self.chain_id == ChainID.ETHEREUM else None
        web3 = Web3(provider, ens=ens)
        for middleware in (
                'validation',  # validation middleware makes an un-needed for us chain ID validation causing 1 extra rpc call per eth_call # noqa: E501
                'gas_price_strategy',  # We do not need to automatically estimate gas
                'gas_estimate',
                'ens_name_to_address',  # we do our own handling for ens names
        ):
            # https://github.com/ethereum/web3.py/blob/bba87a283d802bbebbfe3f8c7dc47560c7a08583/web3/middleware/validation.py#L137-L142  # noqa: E501
            with suppress(ValueError):  # If not existing raises ValueError, so ignore
                web3.middleware_onion.remove(middleware)

        if self.chain_id in (ChainID.OPTIMISM, ChainID.POLYGON_POS, ChainID.ARBITRUM_ONE, ChainID.BASE):  # noqa: E501
            # TODO: Is it needed for all non-mainet EVM chains?
            # https://web3py.readthedocs.io/en/stable/middleware.html#why-is-geth-poa-middleware-necessary
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        return web3, rpc_endpoint

    def attempt_connect(
            self,
            node: NodeName,
            connectivity_check: bool = True,
    ) -> tuple[bool, str]:
        """Attempt to connect to a particular node type

        For our own node if the given rpc endpoint is not the same as the saved one
        the connection is re-attempted to the new one
        """
        message = ''
        node_connected = self.web3_mapping.get(node, None) is not None
        if node_connected:
            return True, f'Already connected to {node} {self.chain_name} node'

        web3, rpc_endpoint = self._init_web3(node)
        try:  # it is here that an actual connection is attempted
            is_connected = web3.is_connected()
        except requests.exceptions.RequestException:
            message = f'Failed to connect to {self.chain_name} node {node} at endpoint {rpc_endpoint}'  # noqa: E501
            log.warning(message)
            return False, message
        except AssertionError:
            # Terrible, terrible hack but needed due to https://github.com/rotki/rotki/issues/1817
            is_connected = False

        if is_connected:
            # Also make sure we are actually connected to the right network
            msg = ''
            try:
                if connectivity_check:
                    try:
                        network_id = int(web3.net.version, 0)  # version can be in hex too. base 0 triggers the prefix check  # noqa: E501
                    except requests.exceptions.RequestException as e:
                        msg = (
                            f'Connected to node {node} at endpoint {rpc_endpoint} but'
                            f'failed to request node version due to {e!s}'
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
                        if isinstance(current_block, int) is False:  # Check for https://github.com/rotki/rotki/issues/6350  # TODO: Check if web3.py v6 has a check for this # noqa: E501
                            raise RemoteError(f'Found non-int current block:{current_block}')
                    except (requests.exceptions.RequestException, RemoteError) as e:
                        msg = f'Could not query latest block due to {e!s}'
                        log.warning(msg)

            except (Web3Exception, ValueError) as e:
                message = (
                    f'Failed to connect to {self.chain_name} node {node} at endpoint '
                    f'{rpc_endpoint} due to {e!s}'
                )
                return False, message

            if node.endpoint.endswith('llamarpc.com'):  # temporary. Seems to sometimes switch
                is_pruned, is_archive = True, False  # between pruned and non-pruned nodes
            elif node.endpoint.endswith('blastapi.io'):  # temporary
                # After the bedrock update blastapi.io switches from archive to non archive nodes
                # It has never reported pruned nodes.
                is_pruned, is_archive = False, False
            else:
                is_pruned, is_archive = self.determine_capabilities(web3)
            log.info(f'Connected {self.chain_name} node {node} at {rpc_endpoint}')
            self.web3_mapping[node] = Web3Node(
                web3_instance=web3,
                is_pruned=is_pruned,
                is_archive=is_archive,
            )
            return True, ''

        # else
        message = f'Failed to connect to {self.chain_name} node {node} at endpoint {rpc_endpoint}'
        log.warning(message)
        return False, message

    def connect_to_multiple_nodes(self, nodes: Sequence[WeightedNode]) -> None:
        for weighted_node in nodes:
            task_name = f'{_connect_task_prefix(self.chain_name)} {weighted_node.node_info.name!s}'
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=task_name,
                exception_is_error=True,
                method=self.attempt_connect,
                node=weighted_node.node_info,
                connectivity_check=True,
            )

    def _query(self, method: Callable, call_order: Sequence[WeightedNode], **kwargs: Any) -> Any:
        """Queries evm related data by performing a query of the provided method to all given nodes

        The first node in the call order that gets a successful response returns.
        If none get a result then RemoteError is raised
        """
        for node_idx, weighted_node in enumerate(call_order):
            node_info = weighted_node.node_info
            web3node = self.web3_mapping.get(node_info, None)
            if web3node is None:
                if node_info.name in self.failed_to_connect_nodes:
                    continue

                if node_info.name != ETHEREUM_ETHERSCAN_NODE_NAME:
                    success, _ = self.attempt_connect(node=node_info)
                    if success is False:
                        self.failed_to_connect_nodes.add(node_info.name)
                        continue

                    if (web3node := self.web3_mapping.get(node_info, None)) is None:
                        log.error(f'Unexpected missing node {node_info} at {self.chain_id}')
                        continue

            if web3node is not None and ((
                method.__name__ in self.methods_that_query_past_data and
                web3node.is_pruned is True
            ) or (
                kwargs.get('block_identifier', 'latest') != 'latest' and
                web3node.is_archive is False
            )):
                # If the block_identifier is different from 'latest'
                # this query should be routed to an archive node
                continue

            try:
                web3 = web3node.web3_instance if web3node is not None else None
                result = method(web3, **kwargs)
            except TransactionNotFound:
                if kwargs.get('must_exist', False) is True:
                    continue  # try other nodes, as transaction has to exist
                return None
            except InvalidAddress as e:
                raise RemoteError(  # no need to try other nodes since its not a node problem.
                    f'Failed to query {node_info.name} for {method!s}: '
                    f'non-checksum address {e.args[1]}',
                ) from e
            except requests.Timeout as e:  # Add node to failed_to_connect_nodes to prevent repeatedly timing out on the same node.  # noqa: E501
                log.warning(
                    f'Timed out while querying {node_info.name} for '
                    f'{method.__name__}: {e!s}. Skipping this node in future queries.',
                )
                self.failed_to_connect_nodes.add(node_info.name)
                self.web3_mapping.pop(node_info, None)
                continue
            except (
                    RemoteError,
                    requests.exceptions.RequestException,
                    BlockchainQueryError,
                    Web3Exception,
                    TypeError,  # happened at the web3 level calling `apply_result_formatters` when the RPC node returned `None` in the response's result # noqa: E501
                    ValueError,  # not removing yet due to possibility of raising from missing trie error  # noqa: E501
            ) as e:
                log.warning(
                    f'Failed to query {node_info.name} with position on the query list {node_idx} '
                    f'for {method.__name__} due to {e!s}',
                )
                # Catch all possible errors here and just try next node call
                continue

            return result

        # no node in the call order list was successfully queried
        log.error(
            f'Failed to query {method.__name__} after trying the following '
            f'nodes: {[x.node_info.name for x in call_order]}. Call parameters were {kwargs}',
        )
        raise RemoteError(f'Error querying information from {self.blockchain!s}. Checks logs to obtain more information')  # noqa: E501

    def _get_latest_block_number(self, web3: Web3 | None) -> int:
        if web3 is not None:
            return web3.eth.block_number

        # else
        return self.etherscan.get_latest_block_number(chain_id=self.chain_id)

    def get_latest_block_number(self, call_order: Sequence[WeightedNode] | None = None) -> int:
        return self._query(
            method=self._get_latest_block_number,
            call_order=call_order if call_order is not None else self.default_call_order(),
        )

    def get_block_by_number(
            self,
            num: int,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[str, Any]:
        return self._query(
            method=self._get_block_by_number,
            call_order=call_order if call_order is not None else self.default_call_order(),
            num=num,
        )

    def _get_block_by_number(self, web3: Web3 | None, num: int) -> dict[str, Any]:
        """Returns the block object corresponding to the given block number

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
        there is a problem with its query.
        - BlockNotFound if number used to lookup the block can't be found. Raised
        by web3.eth.get_block().
        """
        if web3 is None:
            return self.etherscan.get_block_by_number(
                chain_id=self.chain_id,
                block_number=num,
            )

        block_data: MutableAttributeDict = MutableAttributeDict(web3.eth.get_block(num))  # type: ignore # pylint: disable=no-member
        block_data['hash'] = block_data['hash'].to_0x_hex()
        return dict(block_data)

    def get_code(
            self,
            account: ChecksumEvmAddress,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> str:
        return self._query(
            method=self._get_code,
            call_order=call_order if call_order is not None else self.default_call_order(),
            account=account,
        )

    def _get_code(self, web3: Web3 | None, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address as a 0x hex string

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        """
        if web3 is None:
            return self.etherscan.get_code(chain_id=self.chain_id, account=account)

        return web3.eth.get_code(account).to_0x_hex()

    def _call_contract_etherscan(
            self,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            method_name: str,
            arguments: list[Any] | None = None,
    ) -> Any:
        """Performs an eth_call to an evm contract via etherscan

        May raise:
        - RemoteError if there is a problem with
        reaching etherscan or with the returned result
        """
        web3 = Web3()
        given_arguments = arguments or []
        contract = web3.eth.contract(address=contract_address, abi=abi)
        input_data = contract.encode_abi(method_name, args=given_arguments)
        result = self.etherscan.eth_call(
            chain_id=self.chain_id,
            to_address=contract_address,
            input_data=input_data,
        )
        if result == '0x':
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address} for {method_name} '
                f'and chain {self.chain_name} with arguments: {arguments!s} '
                f'via etherscan. Returned 0x result',
            )

        fn_abi = contract._find_matching_fn_abi(
            method_name,
            *given_arguments,
        )
        output_types = get_abi_output_types(fn_abi)
        output_data = web3.codec.decode(output_types, bytes.fromhex(result[2:]))

        if len(output_data) == 1:
            # due to https://github.com/PyCQA/pylint/issues/4114
            return output_data[0]
        return output_data

    def call_contract(
            self,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            method_name: str,
            arguments: list[Any] | None = None,
            call_order: Sequence[WeightedNode] | None = None,
            block_identifier: BlockIdentifier = 'latest',
    ) -> Any:
        return self._query(
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
            web3: Web3 | None,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            method_name: str,
            arguments: list[Any] | None = None,
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
            result = method(*arguments or [])
        except InvalidAddress:
            raise  # propagate to _query() where it's handled properly
        except (Web3Exception, ValueError) as e:
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address}: {e!s}',
            ) from e
        return result

    def _get_transaction_receipt(
            self,
            web3: Web3 | None,
            tx_hash: EVMTxHash,
            must_exist: bool = False,
    ) -> dict[str, Any] | None:
        if tx_hash == GENESIS_HASH:
            return FAKE_GENESIS_TX_RECEIPT
        if web3 is None:
            tx_receipt = self.etherscan.get_transaction_receipt(
                chain_id=self.chain_id,
                tx_hash=tx_hash,
            )
            if tx_receipt is None:
                if must_exist:  # fail, so other nodes can be tried
                    raise RemoteError(f'Querying for {self.chain_name} receipt {tx_hash.hex()} returned None')  # noqa: E501

                return None  # else it does not exist

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
                # This is only implemented for some evm chains
                self._additional_receipt_processing(tx_receipt)
            except (DeserializationError, Web3Exception, ValueError, KeyError) as e:
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

            if must_exist and tx_receipt is None:  # fail, so other nodes can be tried
                raise RemoteError(f'Querying for {self.chain_name} receipt {tx_hash.hex()} returned None')  # noqa: E501

            return tx_receipt

        # Can raise TransactionNotFound if the user's node is pruned and transaction is old
        try:
            tx_receipt = web3.eth.get_transaction_receipt(tx_hash)  # type: ignore
        except TransactionNotFound as e:
            if must_exist:  # fail, so other nodes can be tried
                raise RemoteError(f'Querying for {self.chain_name} receipt {tx_hash.hex()} returned None') from e  # noqa: E501

            raise  # else re-raise e

        return process_result(tx_receipt)

    def maybe_get_transaction_receipt(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
            must_exist: bool = False,
    ) -> dict[str, Any] | None:
        return self._query(
            method=self._get_transaction_receipt,
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=must_exist,
        )

    def get_transaction_receipt(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[str, Any]:
        """Retrieves the transaction receipt for the tx_hash provided.

        This method assumes the tx_hash is present on-chain,
        and we are connected to at least one node that can retrieve it.
        """
        tx_receipt = self.maybe_get_transaction_receipt(
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=True,
        )
        if tx_receipt is None:
            raise RemoteError(f'{self.chain_name} tx_receipt should exist for {tx_hash.hex()}')
        return tx_receipt

    def _get_transaction_by_hash(
            self,
            web3: Web3 | None,
            tx_hash: EVMTxHash,
            must_exist: bool = False,
    ) -> tuple[EvmTransaction, dict[str, Any]] | None:
        if web3 is None:
            tx_data = self.etherscan.get_transaction_by_hash(
                chain_id=self.chain_id,
                tx_hash=tx_hash,
            )
        else:
            tx_data = web3.eth.get_transaction(tx_hash)  # type: ignore
        if tx_data is None:
            if must_exist:  # fail, so other nodes can be tried
                raise RemoteError(f'Querying for {self.chain_name} transaction {tx_hash.hex()} returned None')  # noqa: E501

            return None  # else it does not exist

        try:
            transaction, receipt_data = deserialize_evm_transaction(
                data=tx_data,
                internal=False,
                chain_id=self.chain_id,
                evm_inquirer=self,
            )
        except (DeserializationError, ValueError) as e:
            raise RemoteError(
                f'Couldnt deserialize evm transaction data from {tx_data}. Error: {e!s}',
            ) from e

        if receipt_data is None:
            raise RemoteError(f'{self.chain_name} transaction {tx_hash.hex()} receipt_data is expected to exist')  # noqa: E501  # as etherscan getTransactionByHash does not contains gasUsed'
        return transaction, receipt_data

    def maybe_get_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
            must_exist: bool = False,
    ) -> tuple[EvmTransaction, dict[str, Any]] | None:
        """Gets transaction by hash and raw receipt data"""
        return self._query(
            method=self._get_transaction_by_hash,
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=must_exist,
        )

    def get_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> tuple[EvmTransaction, dict[str, Any]]:
        """Retrieves information about a transaction from its hash.

        This method assumes the tx_hash is present on-chain,
        and we are connected to at least 1 node that can retrieve it.
        """
        result = self.maybe_get_transaction_by_hash(
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=True,
        )
        if result is None:
            raise RemoteError(f'{self.chain_name} transaction {tx_hash.hex()} is expected to exist')  # noqa: E501

        return result

    def get_logs(
            self,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            event_name: str,
            argument_filters: dict[str, Any],
            from_block: int,
            to_block: int | Literal['latest'] = 'latest',
            call_order: Sequence[WeightedNode] | None = None,
            log_iteration_cb: LogIterationCallback | None = None,
            log_iteration_cb_arguments: 'GnosisWithdrawalsQueryParameters | None' = None,
    ) -> list[dict[str, Any]]:
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
        return self._query(
            method=self._get_logs,
            call_order=call_order,
            contract_address=contract_address,
            abi=abi,
            event_name=event_name,
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
            log_iteration_cb=log_iteration_cb,
            log_iteration_cb_arguments=log_iteration_cb_arguments,
        )

    def _get_logs(
            self,
            web3: Web3 | None,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            event_name: str,
            argument_filters: dict[str, Any],
            from_block: int,
            to_block: int | Literal['latest'] = 'latest',
            log_iteration_cb: LogIterationCallback | None = None,
            log_iteration_cb_arguments: 'GnosisWithdrawalsQueryParameters | None' = None,
    ) -> list[dict[str, Any]]:
        """Queries logs of an evm contract
        May raise:

        - EventNotInABI if the given event is not in the ABI
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        """
        try:
            event_abi = find_matching_event_abi(abi=abi, event_name=event_name)
        except ValueError as e:
            raise EventNotInABI from e

        _, filter_args = construct_event_filter_params(
            event_abi=event_abi,
            abi_codec=Web3().codec,
            contract_address=contract_address,
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )

        if event_abi.get('anonymous', False):
            # web3.py does not handle the anonymous events correctly and adds the first topic
            filter_args['topics'] = filter_args['topics'][1:]  # pyright: ignore  # I think FilterParams is not well defined. It always has topics
        events: list[dict[str, Any]] = []
        start_block = from_block

        log.debug(f'Ready to query logs for {filter_args} at {contract_address} ({self.chain_id}) from {start_block} to {to_block}')  # noqa: E501
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
                log_iteration_cb=log_iteration_cb,
                log_iteration_cb_arguments=log_iteration_cb_arguments,
            )
        else:  # etherscan
            until_block = (
                self.etherscan.get_latest_block_number(self.chain_id) if to_block == 'latest' else to_block  # noqa: E501
            )
            blocks_step = 300000
            while start_block <= until_block:
                while True:  # loop to continuously reduce block range if need b
                    end_block = min(start_block + blocks_step, until_block)
                    try:
                        new_events = self.etherscan.get_logs(
                            chain_id=self.chain_id,
                            contract_address=contract_address,
                            topics=filter_args['topics'],  # type: ignore
                            from_block=start_block,
                            to_block=end_block,
                        )
                    except RemoteError as e:
                        if 'Please select a smaller result dataset' in str(e):

                            blocks_step //= 2
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

                if log_iteration_cb is not None:
                    log_iteration_cb(
                        last_block_queried=end_block,
                        filters=argument_filters,
                        new_events=new_events,
                        cb_arguments=log_iteration_cb_arguments,
                    )

                # etherscan will only return 1000 events in one go. If more than 1000
                # are returned such as when no filter args are provided then continue
                # the query from the last block
                if len(new_events) == 1000:
                    start_block = new_events[-1]['blockNumber']
                else:
                    start_block = end_block + 1
                events.extend(new_events)

        return events

    def multicall(
            self,
            calls: list[tuple[ChecksumEvmAddress, str]],
            # only here to comply with multicall_2
            require_success: bool = True,  # pylint: disable=unused-argument
            call_order: Sequence['WeightedNode'] | None = None,
            block_identifier: BlockIdentifier = 'latest',
            calls_chunk_size: int = MULTICALL_CHUNKS,
    ) -> Any:
        """Uses MULTICALL contract. Failure of one call is a failure of the entire multicall.
        source: https://etherscan.io/address/0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441#code
        Can raise:
        - RemoteError
        """
        calls_chunked = list(get_chunks(calls, n=calls_chunk_size))
        output = []
        for call_chunk in calls_chunked:
            multicall_result = self.contract_multicall.call(
                node_inquirer=self,
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
            calls: list[tuple[ChecksumEvmAddress, str]],
            require_success: bool,
            call_order: Sequence['WeightedNode'] | None = None,
            block_identifier: BlockIdentifier = 'latest',
            # only here to comply with multicall
            calls_chunk_size: int = MULTICALL_CHUNKS,  # pylint: disable=unused-argument
    ) -> list[tuple[bool, bytes]]:
        """
        Uses MULTICALL_2 contract. If require success is set to False any call in the list
        of calls is allowed to fail.
        source: https://etherscan.io/address/0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696#code"""
        return self.contract_multicall.call(
            node_inquirer=self,
            method_name='tryAggregate',
            arguments=[require_success, calls],
            call_order=call_order,
            block_identifier=block_identifier,
        )

    def multicall_specific(
            self,
            contract: 'EvmContract',
            method_name: str,
            arguments: list[Any],
            call_order: Sequence['WeightedNode'] | None = None,
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

    def get_multiple_erc20_contract_info(self, addresses: list[ChecksumEvmAddress]) -> None:
        """Query the token information for multiple ERC20 addresses and save them in cache"""
        if len(addresses) == 0:
            return

        contract = EvmContract(address=addresses[0], abi=self.contracts.erc20_abi, deployed_block=0)  # noqa: E501

        for addresses_chunk in get_chunks(addresses, 8):  # chunk number seems to be highest that can work with etherscan url limit  # noqa: E501
            calls = [(address, contract.encode(method_name=prop)) for address in addresses_chunk for prop in ERC20_PROPERTIES]  # noqa: E501

            try:
                # Output contains call status and result
                output = self.multicall_2(require_success=False, calls=calls)
            except RemoteError:
                # If something happens in the connection the output should have
                # the same length as the tuple of properties * addresses
                output = [(False, b'')] * ERC20_PROPERTIES_NUM * len(addresses_chunk)

            for idx, single_output in enumerate(get_chunks(output, ERC20_PROPERTIES_NUM)):
                address = addresses_chunk[idx]
                info = self._process_and_create_erc20_info(
                    output=single_output,
                    address=address,
                )
                self.contract_info_erc20_cache.add(address, info)

    def _process_and_create_erc20_info(
            self,
            output: list[tuple[bool, bytes]],
            address: ChecksumEvmAddress,
    ) -> dict[str, Any]:
        info: dict[str, Any] = {}
        contract = EvmContract(address=address, abi=self.contracts.erc20_abi, deployed_block=0)
        try:
            decoded = self._process_contract_info(
                output=output,
                properties=ERC20_PROPERTIES,
                contract=contract,
                token_kind=EvmTokenKind.ERC20,
            )
        except (OverflowError, DecodingError) as e:
            # This can happen when contract follows the ERC20 standard methods
            # but name and symbol return bytes instead of string. UNIV1 LP is such a case
            # It can also happen if the method is missing and they are all hitting
            # the fallback function. old WETH contract is such a case
            log.error(
                f'{address} failed to decode as ERC20 token. '
                f'Trying with token ABI using bytes. {e!s}',
            )
            abi = self.contracts.univ1lp_abi
            contract = EvmContract(address=address, abi=abi, deployed_block=0)
            decoded = self._process_contract_info(
                output=output,
                properties=ERC20_PROPERTIES,
                contract=contract,
                token_kind=EvmTokenKind.ERC20,
            )
            log.debug(f'{address} was successfully decoded as ERC20 token')

        for prop, value in zip_longest(ERC20_PROPERTIES, decoded):
            if isinstance(value, bytes):
                value = value.rstrip(b'\x00').decode()  # noqa: PLW2901
            info[prop] = value

        return info

    def _query_token_contract(
            self,
            abi: ABI,
            properties: tuple[str, ...],
            address: ChecksumEvmAddress,
    ) -> list[tuple[bool, bytes]]:
        contract = EvmContract(address=address, abi=abi, deployed_block=0)
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

        return output

    def get_erc20_contract_info(self, address: ChecksumEvmAddress) -> dict[str, Any]:
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
        if (cache := self.contract_info_erc20_cache.get(address)) is not None:
            return cache

        output = self._query_token_contract(abi=self.contracts.erc20_abi, properties=ERC20_PROPERTIES, address=address)  # noqa: E501
        info = self._process_and_create_erc20_info(
            output=output,
            address=address,
        )
        self.contract_info_erc20_cache.add(address, info)
        return info

    def get_erc721_contract_info(self, address: ChecksumEvmAddress) -> dict[str, Any]:
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
        if (cache := self.contract_info_erc721_cache.get(address)) is not None:
            return cache

        output = self._query_token_contract(abi=self.contracts.erc721_abi, properties=ERC721_PROPERTIES, address=address)  # noqa: E501

        try:
            decoded = self._process_contract_info(
                output=output,
                properties=ERC721_PROPERTIES,
                contract=EvmContract(address=address, abi=self.contracts.erc721_abi, deployed_block=0),  # noqa: E501
                token_kind=EvmTokenKind.ERC721,
            )
        except (OverflowError, DecodingError) as e:
            raise NotERC721Conformant(f'{address} token does not conform to the ERC721 spec') from e  # noqa: E501

        info: dict[str, Any] = {}
        for prop, value in zip_longest(ERC721_PROPERTIES, decoded):
            if isinstance(value, bytes):
                value = value.rstrip(b'\x00').decode()  # noqa: PLW2901
            info[prop] = value

        self.contract_info_erc721_cache.add(address, info)
        return info

    def _process_contract_info(
            self,
            output: list[tuple[bool, bytes]],
            properties: tuple[str, ...],
            contract: EvmContract,
            token_kind: EvmTokenKind,
    ) -> list[int | (str | bytes) | None]:
        """Decodes information i.e. (decimals, symbol, name) about the token contract.
        - `decimals` property defaults to 18.
        - `name` and `symbol` default to None.
        May raise:
        - OverflowError
        - InsufficientDataBytes (subclass of eth_abi.exceptions.DecodingError)
        - InvalidPointer (subclass of eth_abi.exceptions.DecodingError)
        """
        decoded_contract_info = []
        for method_name, method_value in zip(properties, output, strict=True):
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

    def determine_capabilities(self, web3: Web3) -> tuple[bool, bool]:
        """This method checks for the capabilities of an rpc node. This includes:
        - whether it is an archive node.
        - if the node is pruned or not.

        Returns a tuple of booleans i.e. (is_pruned, is_archived)
        """
        is_archive = self._have_archive(web3)
        is_pruned = self._is_pruned(web3)

        return is_pruned, is_archive

    def get_contract_deployed_block(self, address: ChecksumEvmAddress) -> int | None:
        """Get the deployed block of a contract

        Returns None if the address is not a contract.

        May raise:
        - RemoteError: in case of a problem contacting chain/nodes/remotes"""
        deployed_hash = self.etherscan.get_contract_creation_hash(
            chain_id=self.chain_id,
            address=address,
        )
        if deployed_hash is None:
            return None

        transaction, _ = self.get_transaction_by_hash(deployed_hash)
        return transaction.block_number

    def maybe_timestamp_to_block_range(
            self,
            period: TimestampOrBlockRange,
    ) -> TimestampOrBlockRange:
        if period.range_type == 'timestamps':
            return TimestampOrBlockRange(
                range_type='blocks',
                from_value=self.get_blocknumber_by_time(ts=Timestamp(period.from_value)),
                to_value=self.get_blocknumber_by_time(ts=Timestamp(period.to_value)),
            )

        return period  # no op for block ranges

    # -- methods to be implemented by child classes --

    def get_blocknumber_by_time(
            self,
            ts: Timestamp,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Searches for the blocknumber of a specific timestamp
        - Performs the blockscout api call by default first
        - If RemoteError gets raised it queries etherscan
        May raise RemoteError
        """
        # check if value exists in the cache
        if (block_number := self.timestamp_to_block_cache[self.chain_id].get(ts)) is not None:
            return block_number

        assert self.blockscout is not None, 'Blockscout should be set'
        with suppress(RemoteError):
            block_number = self.blockscout.get_blocknumber_by_time(ts, closest)
            self.timestamp_to_block_cache[self.chain_id].add(key=ts, value=block_number)
            return block_number

        block_number = self.etherscan.get_blocknumber_by_time(
            chain_id=self.chain_id,
            ts=ts,
            closest=closest,
        )
        self.timestamp_to_block_cache[self.chain_id].add(key=ts, value=block_number)
        return block_number

    # -- methods to be optionally implemented by child classes --

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

    def _have_archive(self, web3: Web3) -> bool:
        """Returns a boolean representing if node is an archive one."""
        address_to_check, block_to_check, expected_balance = self._get_archive_check_data()
        balance = self.get_historical_balance(
            address=address_to_check,
            block_number=block_to_check,
            web3=web3,
        )
        return balance == expected_balance

    @abstractmethod
    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        """Returns a tuple of (address, block_number, expected_balance) that can used for
        checking whether a node is an archive one."""

    def _is_pruned(self, web3: Web3) -> bool:
        """Returns a boolean representing if the node is pruned or not."""
        try:
            tx = web3.eth.get_transaction(self._get_pruned_check_tx_hash())  # type: ignore
        except (
                RequestException,
                Web3Exception,
                KeyError,
                ValueError,  # may still be raised in web3 v6 for missing trie error
        ):
            tx = None

        return tx is None

    @abstractmethod
    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        """Returns a transaction hash that can used for checking whether a node is pruned."""

    def _additional_receipt_processing(self, tx_receipt: dict[str, Any]) -> None:
        """Performs additional tx_receipt processing where necessary"""

    @protect_with_lock()
    def ensure_cache_data_is_updated(
            self,
            cache_type: CacheType,
            query_method: Callable,
            force_refresh: bool = False,
            chain_id: ChainID | None = None,
            cache_key_parts: Sequence[str] | None = None,
    ) -> RemoteDataQueryStatus:
        """
        It checks if the cache data is fresh enough and if not, it queries
        the remote sources of the data and stores it to the globaldb cache tables.
        Returns true if the cache was modified or false otherwise.

        If the query_method logic fails due to a RemoteError this function handles
        it and returns False. Other errors aren't handled in this function.

        - cache type: The cache type to check for freshness
        - query_method: The method that queries the remote source for the data
        - save_method: The method that saves the data to the cache tables
        - force_refresh: If True, the cache will be updated even if it is fresh
        - cache_key_parts: The parts to be used to check cache freshness along with cache_type
        """
        if cache_key_parts is None:
            cache_key_parts = []
        if (
            should_update_protocol_cache(cache_type, cache_key_parts) is False and
            force_refresh is False
        ):
            log.debug(f'Not refreshing cache {cache_type}. Queried recently')
            return RemoteDataQueryStatus.NO_UPDATE

        try:
            new_data = query_method(
                inquirer=self,
                cache_type=cache_type,
                msg_aggregator=self.database.msg_aggregator,
            )
        except RemoteError as e:
            log.error(
                f'Failed to call {query_method} when updating cache {cache_type} due to {e}',
            )
            return RemoteDataQueryStatus.FAILED

        return (
            RemoteDataQueryStatus.NEW_DATA if new_data is not None
            else RemoteDataQueryStatus.NO_UPDATE
        )


class EvmNodeInquirerWithDSProxy(EvmNodeInquirer):
    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: Etherscan,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            contracts: EvmContracts,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            dsproxy_registry: 'EvmContract',
            native_token: CryptoAsset,
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
            blockscout: Blockscout | None = None,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=blockchain,
            contracts=contracts,
            contract_scan=contract_scan,
            contract_multicall=contract_multicall,
            rpc_timeout=rpc_timeout,
            native_token=native_token,
            blockscout=blockscout,
        )
        self.proxies_inquirer = EvmProxiesInquirer(
            node_inquirer=self,
            dsproxy_registry=dsproxy_registry,
        )


class DSProxyInquirerWithCacheData(EvmNodeInquirerWithDSProxy):
    """This is the inquirer that needs to be used by chains with modules (protocols)
    that store data in the cache tables of the globaldb. For example velodrome in
    optimism and curve in ethereum store data in cache tables."""

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: Etherscan,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            contracts: EvmContracts,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            dsproxy_registry: 'EvmContract',
            native_token: CryptoAsset,
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
            blockscout: Blockscout | None = None,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=blockchain,
            contracts=contracts,
            contract_scan=contract_scan,
            contract_multicall=contract_multicall,
            rpc_timeout=rpc_timeout,
            native_token=native_token,
            dsproxy_registry=dsproxy_registry,
            blockscout=blockscout,
        )
