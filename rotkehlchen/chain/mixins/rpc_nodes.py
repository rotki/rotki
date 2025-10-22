import json
import logging
import random
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from urllib.parse import urlparse

import requests
from ens import ENS
from solana.exceptions import SolanaRpcException
from solana.rpc.api import Client
from solana.rpc.core import RPCException
from solders.solders import SerdeJSONError
from typing_extensions import NamedTuple
from web3 import HTTPProvider, Web3
from web3.exceptions import Web3Exception
from web3.middleware import ExtraDataToPOAMiddleware

from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.solana.constants import SOLANA_GENESIS_BLOCK_HASH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tests.utils.globaldb import Literal
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


WEB3_NODE_TYPE = TypeVar('WEB3_NODE_TYPE', Web3, Client)
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RPCNode(NamedTuple, Generic[WEB3_NODE_TYPE]):
    """This represents an RPC node with its capabilities."""
    rpc_client: WEB3_NODE_TYPE
    is_pruned: bool
    is_archive: bool


class RPCManagerMixin(ABC, Generic[WEB3_NODE_TYPE]):
    """
    Mixin that provides logic for managing RPC nodes. It tracks active connections
    and implements the core mechanisms for connecting to them.

    This mixin is intended for chains that support RPCs, such as EVM-based chains
    and Solana. It is not used directly, since each chain introduces small
    differences in behavior. Instead, chain-specific mixins (e.g. `EVMRPCMixin`,
    `SolanaRPCMixin`) extend this class and adjust parameters such as
    `WEB3_NODE_TYPE` accordingly.
    """
    database: 'DBHandler'
    greenlet_manager: GreenletManager
    blockchain: SupportedBlockchain
    chain_name: str
    rpc_timeout: int

    @staticmethod
    def _connect_task_prefix(chain_name: str) -> str:
        """Helper function to create the connection task greenlet name"""
        return f'Attempt connection to {chain_name} node'

    def __init__(self) -> None:
        self.rpc_mapping: dict[NodeName, RPCNode[WEB3_NODE_TYPE]] = {}
        # failed_to_connect_nodes keeps the nodes that we couldn't connect while
        # doing remote queries so they aren't tried again if they get chosen. At the
        # moment of writing this we don't remove entries from the set after some time.
        # To force the app to retry a node a restart is needed.
        self.failed_to_connect_nodes: set[str] = set()

    def connected_to_any_node(self) -> bool:
        """Check if there are any currently connected nodes.
        This does not include nodes that are available but not yet connected.
        """
        return len(self.rpc_mapping) != 0

    def get_own_node(self) -> WEB3_NODE_TYPE | None:
        """Returns a single connected node that is labeled as owned.
        If there aren't owned nodes it returns None.
        """
        for node, rpc_node in self.rpc_mapping.items():
            if node.owned:
                return rpc_node.rpc_client
        return None

    def get_own_node_info(self) -> NodeName | None:
        """Get the node info for the any connected rpc node"""
        for node in self.rpc_mapping:
            if node.owned:
                return node
        return None

    def get_connected_nodes(self) -> list[NodeName]:
        """Get all currently connected nodes"""
        return list(self.rpc_mapping.keys())

    def maybe_connect_to_nodes(self, when_tracked_accounts: bool) -> None:
        """Start async connect to the saved nodes for the given blockchain if needed.

        If `when_tracked_accounts` is True then it will connect when we have some
        tracked accounts in the DB. Otherwise when we have none.

        In ethereum case always connect to nodes. Needed for ENS resolution.
        For other EVM chains we respect `when_tracked_accounts`.
        """
        if self.connected_to_any_node() or self.greenlet_manager.has_task(self._connect_task_prefix(self.chain_name)):  # noqa: E501
            return

        with self.database.conn.read_ctx() as cursor:
            accounts = self.database.get_blockchain_accounts(cursor)

        if (
            (tracked_accounts_num := len(accounts.get(self.blockchain)) != 0 and when_tracked_accounts) or  # noqa: E501
            (tracked_accounts_num == 0 and
            (when_tracked_accounts is False or self.blockchain == SupportedBlockchain.ETHEREUM))
        ):
            rpc_nodes = self.database.get_rpc_nodes(blockchain=self.blockchain, only_active=True)
            self.connect_to_multiple_nodes(rpc_nodes)

    @abstractmethod
    def attempt_connect(
            self,
            node: NodeName,
            connectivity_check: bool = True,
    ) -> tuple[bool, str]:
        """Attempt to connect to a particular node type"""

    def connect_to_multiple_nodes(self, nodes: Sequence['WeightedNode']) -> None:
        task_prefix = self._connect_task_prefix(self.chain_name)
        for weighted_node in nodes:
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'{task_prefix} {weighted_node.node_info.name!s}',
                exception_is_error=True,
                method=self.attempt_connect,
                node=weighted_node.node_info,
                connectivity_check=True,
            )

    def default_call_order(self) -> list['WeightedNode']:
        """Default call order for RPCx nodes

        Own node always has preference. Then all other node types are randomly queried
        in sequence depending on a weighted probability.
        """
        selection, owned_nodes = [], []
        for wnode in self.database.get_rpc_nodes(
            blockchain=self.blockchain,
            only_active=True,
        ):
            if wnode.node_info.owned is False:
                selection.append(wnode)
            else:
                owned_nodes.append(wnode.node_info)

        ordered_list = []
        while len(selection) != 0:
            weights = [float(entry.weight) for entry in selection]
            node = random.choices(selection, weights, k=1)
            ordered_list.append(node[0])
            selection.remove(node[0])

        if len(owned_nodes) != 0:
            # Assigning one is just a default since we always use it.
            # The weight is only important for the other nodes since they
            # are selected using this parameter
            ordered_list = [WeightedNode(node_info=node, weight=ONE, active=True) for node in owned_nodes] + ordered_list  # noqa: E501
        return ordered_list


class EVMRPCMixin(RPCManagerMixin['Web3']):
    """Implementation of RPCManagerMixin to use `Web3.py"""

    blockchain: SUPPORTED_EVM_CHAINS_TYPE
    chain_id: SUPPORTED_CHAIN_IDS
    _have_archive: Callable[[Web3], bool]  # implemented in the inquirer since it needs methods from there  # noqa: E501

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.etherscan_node = ETHEREUM_ETHERSCAN_NODE

    def determine_capabilities(self, web3: Web3) -> tuple[bool, bool]:
        """This method checks for the capabilities of an rpc node. This includes:
        - whether it is an archive node.
        - if the node is pruned or not.

        Returns a tuple of booleans i.e. (is_pruned, is_archived)
        """
        return self._have_archive(web3), self._is_pruned(web3)

    def _is_pruned(self, web3: Web3) -> bool:
        """Returns a boolean representing if the node is pruned or not."""
        try:
            tx = web3.eth.get_transaction(self._get_pruned_check_tx_hash())  # type: ignore
        except (
                requests.RequestException,
                Web3Exception,
                KeyError,
                ValueError,  # may still be raised in web3 v6 for missing trie error
        ):
            tx = None

        return tx is None

    @abstractmethod
    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        """Returns a tuple of (address, block_number, expected_balance) that can used for
        checking whether a node is an archive one."""

    @abstractmethod
    def _get_pruned_check_tx_hash(self) -> 'EVMTxHash':
        """Returns a transaction hash that can used for checking whether a node is pruned."""

    def _init_web3(self, node: NodeName) -> tuple[Web3, str]:
        """Initialize a new Web3 object based on a given endpoint"""
        provider = HTTPProvider(
            endpoint_uri=(rpc_endpoint := f'http://{node.endpoint}' if not urlparse(node.endpoint).scheme else node.endpoint),  # noqa: E501
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
        """Attempt to connect to a particular web3 node

        For our own node if the given rpc endpoint is not the same as the saved one
        the connection is re-attempted to the new one
        """
        if node in self.rpc_mapping:
            return True, f'Already connected to {node} {self.chain_name} node'

        web3, rpc_endpoint = self._init_web3(node)
        try:  # it is here that an actual connection is attempted
            is_connected = web3.is_connected()
        except requests.RequestException:
            message = f'Failed to connect to {self.chain_name} node {node} at endpoint {rpc_endpoint}'  # noqa: E501
            log.warning(message)
            return False, message
        except json.JSONDecodeError as e:
            message = f'Failed to connect to {self.chain_name} node {node} at endpoint {rpc_endpoint} due to invalid JSON response: {e!s}'  # noqa: E501
            log.warning(message)
            return False, message
        except AssertionError:
            # Terrible, terrible hack but needed due to https://github.com/rotki/rotki/issues/1817
            is_connected = False

        if is_connected:
            try:  # Also make sure we are actually connected to the right network
                if connectivity_check:
                    try:
                        network_id = int(web3.net.version, 0)  # version can be in hex too. base 0 triggers the prefix check  # noqa: E501
                    except requests.RequestException as e:
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
                    except (requests.RequestException, RemoteError) as e:
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
                is_archive, is_pruned = False, False
            else:
                is_archive, is_pruned = self.determine_capabilities(web3)
            log.info(f'Connected {self.chain_name} node {node} at {rpc_endpoint}')
            self.rpc_mapping[node] = RPCNode(
                rpc_client=web3,
                is_pruned=is_pruned,
                is_archive=is_archive,
            )
            return True, ''

        # else
        message = f'Failed to connect to {self.chain_name} node {node} at endpoint {rpc_endpoint}'
        log.warning(message)
        return False, message

    def default_call_order(self, skip_etherscan: bool = False) -> list['WeightedNode']:
        """Default call order for evm nodes

        Own node always has preference. Then all other node types are randomly queried
        in sequence depending on a weighted probability.

        If skip_etherscan is set to True then etherscan is not included in the list of
        nodes to query.
        """
        ordered_list = super().default_call_order()
        if not skip_etherscan:  # explicitly adding at the end to minimize etherscan API queries
            ordered_list.append(self.etherscan_node)

        return ordered_list


class SolanaRPCMixin(RPCManagerMixin['Client']):
    blockchain: Literal[SupportedBlockchain.SOLANA]
    chain_name = SupportedBlockchain.SOLANA.serialize()

    def attempt_connect(
            self,
            node: NodeName,
            connectivity_check: bool = True,
    ) -> tuple[bool, str]:
        """Attempt to connect to a particular solana node

        For our own node if the given rpc endpoint is not the same as the saved one
        the connection is re-attempted to the new one
        """
        if self.rpc_mapping.get(node, None) is not None:
            return True, f'Already connected to {node} {self.chain_name} node'

        try:
            (client := Client(
                endpoint=node.endpoint,
                timeout=self.rpc_timeout,
            )).is_connected()
        except (RPCException, SolanaRpcException, SerdeJSONError) as e:
            return (
                False,
                f'Failed to connect to Solana RPC at {node.endpoint} due to {e}',
            )

        log.info(f'Connected Solana node {node} at {node.endpoint}')
        self.rpc_mapping[node] = RPCNode(
            rpc_client=client,
            is_pruned=False,
            is_archive=self._is_archive(client),
        )

        return True, ''

    @staticmethod
    def _is_archive(client: Client) -> bool:
        """Returns a boolean representing if the node is an archive one."""
        try:
            return client.get_block(0).value.blockhash == SOLANA_GENESIS_BLOCK_HASH
        except (RPCException, SolanaRpcException, SerdeJSONError):
            return False
