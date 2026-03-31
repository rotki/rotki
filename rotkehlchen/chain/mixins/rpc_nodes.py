import json
import logging
import random
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final, Generic, Literal, TypeVar
from urllib.parse import urlparse

import requests
from ens import ENS
from httpx import HTTPStatusError, ReadTimeout
from solana.exceptions import SolanaRpcException
from solana.rpc.api import Client
from solana.rpc.core import RPCException
from solana.rpc.types import MemcmpOpts
from solders.solders import SerdeJSONError
from typing_extensions import NamedTuple
from web3 import HTTPProvider, Web3
from web3.exceptions import Web3Exception
from web3.middleware import ExtraDataToPOAMiddleware

from rotkehlchen.chain.ethereum.constants import EVM_INDEXERS_NODE
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.solana.constants import (
    SOLANA_GENESIS_BLOCK_HASH,
    STAKE_ACCOUNT_WITHDRAWER_OFFSET,
    STAKE_PROGRAM_ID,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


WEB3_NODE_TYPE = TypeVar('WEB3_NODE_TYPE', Web3, Client)
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

RATE_LIMIT_COOLDOWN_SECS: Final = 300  # 5 minutes before retrying a rate-limited node
# Patterns indicating a rate-limit response in a provider's error message
RATE_LIMIT_PATTERNS: Final = ('rate limit', 'too many requests', 'rate_limit', '429')


class NodeStatus(StrEnum):
    READY = 'ready'
    COOLING_DOWN = 'cooling_down'


def _normalize_endpoint(endpoint: str) -> str:
    """Normalize an RPC endpoint URL to a stable identity key.

    Two endpoints that differ only by scheme casing, trailing slash, or default port
    will produce the same key, so they share runtime state.

    TODO: Normalize/canonicalize endpoints before persisting them in DB.
    We currently store raw endpoint strings, so canonical-equivalent endpoints can be
    saved as separate rows and need runtime normalization.
    """
    if '://' not in endpoint:
        endpoint = f'http://{endpoint}'
    parsed = urlparse(endpoint)
    host = (parsed.hostname or '').lower()
    port = parsed.port
    path = parsed.path.rstrip('/')
    # Omit port when it is the default for the scheme
    if port and not (
        (parsed.scheme == 'https' and port == 443) or
        (parsed.scheme == 'http' and port == 80)
    ):
        return f'{parsed.scheme}://{host}:{port}{path}'
    return f'{parsed.scheme}://{host}{path}'


@dataclass
class NodeRuntimeState:
    """In-memory runtime health state for a single RPC endpoint.

    This is keyed by normalized endpoint URL and reset on restart.
    It is separate from DB configuration state (WeightedNode).
    """
    status: NodeStatus
    cooldown_until: Timestamp | None = None
    last_success_ts: Timestamp | None = None
    last_error_ts: Timestamp | None = None
    last_error_kind: str | None = None
    consecutive_failures: int = 0


def _is_rate_limit_error(exc: Exception) -> bool:
    """Returns True when exc indicates the provider is rate-limiting us."""
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        return exc.response.status_code in (429, 403)
    err = str(exc).lower()
    return any(p in err for p in RATE_LIMIT_PATTERNS)


class RPCNode(NamedTuple, Generic[WEB3_NODE_TYPE]):
    """This represents an RPC node with its capabilities."""
    rpc_client: WEB3_NODE_TYPE
    is_pruned: bool
    is_archive: bool
    supports_program_accounts: bool = False


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
        # Per-endpoint runtime health: keyed by _normalize_endpoint(endpoint).
        # Reset on restart; never persisted.
        self._node_runtime_state: dict[str, NodeRuntimeState] = {}
        # Cached list of active configured nodes for this chain.
        # None means the cache is stale and must be reloaded from DB on next access.
        self._configured_nodes_cache: list[WeightedNode] | None = None

    def connected_to_any_node(self) -> bool:
        """Check if there are any currently connected nodes.
        This does not include nodes that are available but not yet connected.
        """
        return len(self.rpc_mapping) != 0

    def get_own_node_info(self) -> NodeName | None:
        """Get the node info for the any connected rpc node"""
        for node in self.rpc_mapping:
            if node.owned:
                return node
        return None

    def get_connected_nodes(self) -> list[NodeName]:
        """Get all currently connected nodes"""
        return list(self.rpc_mapping.keys())

    def _get_configured_nodes(self) -> list['WeightedNode']:
        """Return the cached list of active configured nodes, loading from DB if needed."""
        if self._configured_nodes_cache is None:
            self._configured_nodes_cache = list(
                self.database.get_rpc_nodes(blockchain=self.blockchain, only_active=True),
            )
        return self._configured_nodes_cache

    def invalidate_nodes_cache(self) -> None:
        """Mark the configured-node cache as stale.

        Must be called after any RPC configuration change (add / edit / delete / enable).
        """
        self._configured_nodes_cache = None

    def _endpoint_key(self, node: 'NodeName') -> str:
        return _normalize_endpoint(node.endpoint)

    def mark_node_success(self, node: 'NodeName') -> None:
        """Record a successful query."""
        key = self._endpoint_key(node)
        now = ts_now()
        existing = self._node_runtime_state.get(key)
        if existing is not None:
            # Mutate in-place — avoids object allocation on the hot path
            existing.status = NodeStatus.READY
            existing.cooldown_until = None
            existing.consecutive_failures = 0
            existing.last_success_ts = now
        else:
            self._node_runtime_state[key] = NodeRuntimeState(
                status=NodeStatus.READY,
                last_success_ts=now,
            )

    def mark_node_rate_limited(self, node: 'NodeName', error: str) -> None:
        """Put a node into cooldown after a rate-limit response (HTTP 429 / 403 / message)."""
        key = self._endpoint_key(node)
        now = ts_now()
        existing = self._node_runtime_state.get(key)
        consecutive_failures = (existing.consecutive_failures if existing else 0) + 1
        self._node_runtime_state[key] = NodeRuntimeState(
            status=NodeStatus.COOLING_DOWN,
            cooldown_until=Timestamp(now + RATE_LIMIT_COOLDOWN_SECS),
            last_success_ts=existing.last_success_ts if existing else None,
            last_error_ts=now,
            last_error_kind='rate_limited',
            consecutive_failures=consecutive_failures,
        )
        log.warning(
            f'Node {node.name} ({key}) is rate-limited. '
            f'Cooling down for {RATE_LIMIT_COOLDOWN_SECS}s. Error: {error}',
        )

    def mark_node_failure(self, node: 'NodeName', error: str) -> None:
        """Record a non-rate-limit failure for a node."""
        key = self._endpoint_key(node)
        now = ts_now()
        existing = self._node_runtime_state.get(key)
        consecutive_failures = (existing.consecutive_failures if existing else 0) + 1
        self._node_runtime_state[key] = NodeRuntimeState(
            # Ordinary failure: stay ready so the node is tried again later.
            status=NodeStatus.READY,
            cooldown_until=existing.cooldown_until if existing else None,
            last_success_ts=existing.last_success_ts if existing else None,
            last_error_ts=now,
            last_error_kind='failure',
            consecutive_failures=consecutive_failures,
        )

    def is_node_in_cooldown(self, node: 'NodeName') -> bool:
        """Return True if the node is currently in the rate-limit cooldown window."""
        key = self._endpoint_key(node)
        state = self._node_runtime_state.get(key)
        if state is None or state.status != NodeStatus.COOLING_DOWN:
            return False
        if state.cooldown_until is not None and ts_now() >= state.cooldown_until:
            # Cooldown window has expired — transition back to ready
            state.status = NodeStatus.READY
            state.cooldown_until = None
            return False
        return True

    def get_runtime_state(self, node: 'NodeName') -> NodeRuntimeState | None:
        """Return the current runtime state for a node, or None if not yet tracked."""
        return self._node_runtime_state.get(self._endpoint_key(node))

    def clear_runtime_state(self, node: 'NodeName') -> None:
        """Remove all runtime state for a node (call when a node is deleted from config)."""
        self._node_runtime_state.pop(self._endpoint_key(node), None)

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

        tracked_accounts_num = len(accounts.get(self.blockchain))
        if (
            (tracked_accounts_num != 0 and when_tracked_accounts) or
            (tracked_accounts_num == 0 and (
                when_tracked_accounts is False or self.blockchain == SupportedBlockchain.ETHEREUM
            ))
        ):
            # Re-read configured nodes at connect time. This avoids using stale cache
            # entries when node configuration changed before first connection attempt.
            self.invalidate_nodes_cache()
            self.connect_to_multiple_nodes(self._get_configured_nodes())

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
        """Default call order for RPC nodes.

        Builds the order from the in-memory configured-node cache (no DB hit).
        Ready owned nodes always come first. Nodes currently in cooldown are excluded.
        Remaining public nodes are ordered by weighted random selection.
        """
        selection, owned_nodes = [], []
        for wnode in self._get_configured_nodes():
            if self.is_node_in_cooldown(wnode.node_info):
                continue

            if wnode.node_info.owned is False:
                selection.append(wnode)
            else:
                owned_nodes.append(wnode.node_info)

        ordered_list: list[WeightedNode] = []
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
        self.indexers_node = EVM_INDEXERS_NODE

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
            # https://github.com/ethereum/web3.py/blob/bba87a283d802bbebbfe3f8c7dc47560c7a08583/web3/middleware/validation.py#L137-L142
            with suppress(ValueError):  # If not existing raises ValueError, so ignore
                web3.middleware_onion.remove(middleware)

        if self.chain_id in (ChainID.OPTIMISM, ChainID.POLYGON_POS, ChainID.ARBITRUM_ONE, ChainID.BASE, ChainID.BINANCE_SC):  # noqa: E501
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

    def default_call_order(self, skip_indexers: bool = False) -> list['WeightedNode']:
        """Default call order for evm nodes

        Own node always has preference. Then all other node types are randomly queried
        in sequence depending on a weighted probability.

        If skip_indexers is set to True then the indexers are not included in the list of
        nodes to query.
        """
        ordered_list = super().default_call_order()
        if not skip_indexers:  # explicitly adding at the end to minimize indexer API queries
            ordered_list.append(self.indexers_node)

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
            supports_program_accounts=self._supports_program_accounts(client),
        )

        return True, ''

    @staticmethod
    def _is_archive(client: Client) -> bool:
        """Returns a boolean representing if the node is an archive one."""
        try:
            return client.get_block(0).value.blockhash == SOLANA_GENESIS_BLOCK_HASH
        except (RPCException, SolanaRpcException, SerdeJSONError):
            return False

    @staticmethod
    def _supports_program_accounts(client: Client) -> bool:
        """Probe whether the node supports getProgramAccounts by issuing a minimal
        query against the stake program with a filter guaranteed to match nothing
        (zeroed-out withdrawer). If the node rejects the method we mark it as
        unsupported so we never waste time retrying on it later."""
        try:
            client.get_program_accounts(
                pubkey=STAKE_PROGRAM_ID,
                filters=[MemcmpOpts(
                    offset=STAKE_ACCOUNT_WITHDRAWER_OFFSET,
                    bytes='11111111111111111111111111111111',  # system program address - no stake account has this as withdrawer  # noqa: E501
                )],
            )
        except (RPCException, SolanaRpcException, SerdeJSONError, HTTPStatusError, ReadTimeout):
            return False
        else:
            return True
