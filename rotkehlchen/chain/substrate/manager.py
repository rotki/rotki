import logging
from collections.abc import Callable, Iterable, Sequence
from functools import wraps
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import Any, NamedTuple, cast
from urllib.parse import urlparse

import gevent
import requests
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import BlockNotFound, SubstrateRequestException
from websocket import WebSocketException

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.constants.assets import A_DOT, A_KSM
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int_from_str
from rotkehlchen.types import SUPPORTED_SUBSTRATE_CHAINS_TYPE, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.serialization import jsonloads_dict

from .types import (
    BlockNumber,
    DictNodeNameNodeAttributes,
    KusamaNodeName,
    NodeName,
    NodeNameAttributes,
    NodesCallOrder,
    PolkadotNodeName,
    SubstrateAddress,
    SubstrateChainId,
)
from .utils import SUBSTRATE_NODE_CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Number of blocks after which to consider not synced
SUBSTRATE_BLOCKS_THRESHOLD = 10


class SubstrateChainProperties(NamedTuple):
    """These properties are populated straight from the blockchain.

    Chain properties from `<SubstrateInterface>.properties` response:
    - 'ss58Format' (int): the default Substrate address format of the chain.
    - 'tokenDecimals' (int): the number of decimals of the native token.
    - 'tokenSymbol' (str): the identifier of the native token.

    External Address Format (SS58) documentation:
    https://github.com/paritytech/substrate/wiki/External-Address-Format-(SS58)
    """
    ss58_format: int
    token: CryptoAsset
    token_decimals: FVal


def request_available_nodes(func: Callable) -> Callable:
    """Given a function calls it sequentially for each available node. If the
    call is successful returns, otherwise calls it again for the next node.

    How to use: decorate any SubstrateManager instance method that requests the
    chain via `node_interface` (<SubstrateInterface>). Make sure `node_interface`
    is a keyword argument of the decorated instance method.

    NB: every time a new method is decorated with this function or an existing
    one is modified, make sure its exceptions are handled as expected. It may
    require to extend the exceptions tuple of the try...except block that wraps
    the method call.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not isinstance(args[0], SubstrateManager):
            raise AssertionError(
                f'Unexpected first positional argument: {args[0]}. This function '
                f'must be called with SubstrateManager instance methods',
            )

        manager = args[0]
        if len(manager.available_nodes_call_order) == 0:
            raise RemoteError(f'{manager.chain} has no nodes available')

        args_ = args[1:]
        kwargs_ = kwargs.copy()
        requested_nodes = []
        for node, node_attributes in manager.available_nodes_call_order:
            kwargs_.update({'node_interface': node_attributes.node_interface})
            try:
                result = func(manager, *args_, **kwargs_)
            except RemoteError as e:
                requested_nodes.append(str(node))
                endpoint = node_attributes.node_interface.url
                log.warning(
                    f'{manager.chain} {func.__name__!r} failed to request via '
                    f'{node} node at endpoint {endpoint} due to: {e!s}.',
                    args=args[1:],
                    kwargs=kwargs_,
                )
                continue

            return result

        raise RemoteError(
            f'{manager.chain} request failed after trying the following nodes: '
            f'{", ".join(requested_nodes)}',
        )
    return wrapper


class SubstrateManager(ChainManager[SubstrateAddress]):
    def __init__(
            self,
            chain: SUPPORTED_SUBSTRATE_CHAINS_TYPE,
            greenlet_manager: GreenletManager,
            msg_aggregator: MessagesAggregator,
            connect_at_start: Sequence[NodeName],
            connect_on_startup: bool,
            own_rpc_endpoint: str,
    ) -> None:
        """An interface to any Substrate chain supported by rotki.

        It uses Polkascan py-substrate-interface for interacting with the
        substrate blockchains and the Subscan API as a chain explorer.

        Official substrate chains documentation:
        https://substrate.dev/rustdocs/v2.0.0/sc_service/index.html
        https://wiki.polkadot.network/kusama/kusama-getting-started/
        https://wiki.polkadot.network/en/

        External Address Format (SS58) documentation:
        https://github.com/paritytech/substrate/wiki/External-Address-Format-(SS58)

        Polkascan py-scale-codec:
        https://github.com/polkascan/py-scale-codec/tree/master

        Polkascan py-substrate-interface:
        https://github.com/polkascan/py-substrate-interface
        https://jamdottech.github.io/py-polkadot-sdk/reference/base/

        Subscan API documentation:
        https://docs.api.subscan.io
        """
        log.debug(f'Initializing {chain} manager')
        self.chain = chain
        self.greenlet_manager = greenlet_manager
        self.msg_aggregator = msg_aggregator
        self.connect_at_start = connect_at_start
        self.own_rpc_endpoint = own_rpc_endpoint
        self.available_node_attributes_map: DictNodeNameNodeAttributes = {}
        self.available_nodes_call_order: NodesCallOrder = []
        self.chain_properties: SubstrateChainProperties
        if connect_on_startup and len(connect_at_start) != 0:
            self.attempt_connections()
        else:
            log.warning(
                f"{self.chain} manager won't attempt to connect to nodes",
                connect_at_start=connect_at_start,
                connect_on_startup=connect_on_startup,
                own_rpc_endpoint=own_rpc_endpoint,
            )

    def _check_chain(self, node_interface: SubstrateInterface) -> None:
        """Validate a node connects to the expected chain.

        May raise:
        - RemoteError: the chain request fails, or the chain is not the
        expected one.
        """
        # Check connection and chain ID
        chain = self._get_chain_id(node_interface=node_interface)
        if chain != str(self.chain).capitalize():
            message = (
                f'{self.chain} found unexpected chain {chain} when attempted '
                f'to connect to node at endpoint: {node_interface.url}, '
            )
            log.error(message)
            raise RemoteError(message)

    def _check_node_synchronization(self, node_interface: SubstrateInterface) -> BlockNumber:
        """Check the node synchronization comparing the last block obtained via
        the node interface against the last block obtained via Subscan API.
        Return the last block obtained via the node interface.

        May raise:
        - RemoteError: the last block/chain metadata requests fail or
        there is an error deserializing the chain metadata.
        """
        # Last block via node interface
        last_block = self._get_last_block(node_interface=node_interface)

        # Last block via Subscan API
        try:
            chain_metadata = self._request_chain_metadata()
        except RemoteError:
            log.warning(
                f'Unable to verify that {self.chain} node at endpoint {node_interface.url} '
                f'is synced with the chain. Balances and other queries may be incorrect.',
            )
            return last_block

        # Check node synchronization
        try:
            metadata_last_block = BlockNumber(
                deserialize_int_from_str(
                    symbol=chain_metadata['data']['blockNum'],
                    location='subscan api',
                ),
            )
        except (KeyError, DeserializationError) as e:
            message = f'{self.chain} failed to deserialize the chain metadata response: {e!s}.'
            log.error(message, chain_metadata=chain_metadata)
            raise RemoteError(message) from e

        log.debug(
            f'{self.chain} subscan API metadata last block',
            metadata_last_block=metadata_last_block,
        )
        if metadata_last_block - last_block > SUBSTRATE_BLOCKS_THRESHOLD:
            self.msg_aggregator.add_warning(
                f'Found that {self.chain} node at endpoint {node_interface.url} '
                f'is not synced with the chain. Node last block is {last_block}, '
                f'expected last block is {metadata_last_block}. '
                f'Balances and other queries may be incorrect.',
            )

        return last_block

    def _connect_node(
            self,
            node: NodeName,
            endpoint: str,
    ) -> tuple[bool, str]:
        """Attempt to connect to a node, check its status and store its
        attributes (e.g. interface, weight) in the available nodes map.

        May raise:
        - RemoteError: connecting to a node fails at any of the steps executed.
        """
        if node in self.available_node_attributes_map:
            message = f'{self.chain} already connected to {node} node at endpoint: {endpoint}.'
            return True, message

        try:
            node_interface = self._get_node_interface(endpoint)
            self._check_chain(node_interface)
            last_block = self._check_node_synchronization(node_interface)
            self._set_chain_properties(node_interface)
        except RemoteError as e:
            message = (
                f'{self.chain} failed to connect to {node} at endpoint {endpoint}, '
                f'due to {e!s}.'
            )
            return False, message

        log.info(f'{self.chain} connected to {node} node at endpoint: {node_interface.url}.')
        node_attributes = NodeNameAttributes(
            node_interface=node_interface,
            weight_block=last_block,
        )
        self.available_node_attributes_map[node] = node_attributes
        self._set_available_nodes_call_order()
        return True, ''

    @staticmethod
    def _format_own_rpc_endpoint(endpoint: str) -> str:
        parsed = urlparse(endpoint)
        if not parsed.scheme or parsed.path.isnumeric():
            return f'http://{endpoint}'
        return endpoint

    def _get_account_balance(
            self,
            account: SubstrateAddress,
            node_interface: SubstrateInterface,
    ) -> FVal:
        """Given an account get its amount of chain native token.

        More information about an account balance in the Substrate AccountData
        documentation.
        """
        log.debug(
            f'{self.chain} querying {self.chain_properties.token.identifier} balance',
            url=node_interface.url,
            account=account,
        )
        try:
            with gevent.Timeout(SUBSTRATE_NODE_CONNECTION_TIMEOUT):
                result = node_interface.query(
                    module='System',
                    storage_function='Account',
                    params=[account],
                )
        except (
                requests.exceptions.RequestException,
                SubstrateRequestException,
                ValueError,
                WebSocketException,
                gevent.Timeout,
                BlockNotFound,
                AttributeError,  # happens in substrate library when timeout occurs some times
        ) as e:
            msg = str(e)
            if isinstance(e, gevent.Timeout):
                msg = f'a timeout of {msg}'
            message = (
                f'{self.chain} failed to request {self.chain_properties.token.identifier} account '
                f'balance at endpoint {node_interface.url} due to: {msg}'
            )
            log.error(message, account=account)
            raise RemoteError(message) from e

        log.debug(
            f'{self.chain} account balance',
            account=account,
            result=result,
        )

        balance = ZERO
        if result is not None:
            account_data = result.value['data']
            balance = (
                FVal(account_data['free'] + account_data['reserved']) /
                FVal('10') ** self.chain_properties.token_decimals
            )

        return balance

    def _get_chain_id(self, node_interface: SubstrateInterface) -> SubstrateChainId:
        """Return the chain identifier (name for substrate chains)"""
        log.debug(f'{self.chain} querying chain ID', url=node_interface.url)
        try:
            chain_id = node_interface.chain
        except (
            requests.exceptions.RequestException,
            SubstrateRequestException,
            WebSocketException,
        ) as e:
            message = (
                f'{self.chain} failed to request chain ID '
                f'at endpoint: {node_interface.url} due to: {e!s}.'
            )
            log.error(message)
            raise RemoteError(message) from e

        log.debug(f'{self.chain} chain ID', chain_id=chain_id)
        return SubstrateChainId(chain_id)

    def _get_chain_properties(
            self,
            node_interface: SubstrateInterface,
    ) -> SubstrateChainProperties:
        """Return the chain properties"""
        log.debug(f'{self.chain} querying chain properties', url=node_interface.url)
        try:
            properties = node_interface.properties
        except (
            requests.exceptions.RequestException,
            SubstrateRequestException,
            WebSocketException,
        ) as e:
            message = (
                f'{self.chain} failed to request chain properties '
                f'at endpoint: {node_interface.url} due to: {e!s}.'
            )
            log.error(message)
            raise RemoteError(message) from e

        log.debug(f'{self.chain} chain properties', properties=properties)
        try:
            chain_properties = SubstrateChainProperties(
                ss58_format=properties['ss58Format'],
                token=CryptoAsset(properties['tokenSymbol']),
                token_decimals=FVal(properties['tokenDecimals']),
            )
        except (KeyError, UnknownAsset) as e:
            message = f'{self.chain} failed to deserialize properties due to: {e!s}.'
            log.error(message, properties=properties)
            raise RemoteError(message) from e

        return chain_properties

    def _get_last_block(self, node_interface: SubstrateInterface) -> BlockNumber:
        """Return the chain height.

        May raise:
        - RemoteError if there is an error
        """
        log.debug(f'{self.chain} querying last block', url=node_interface.url)
        try:
            last_block = node_interface.get_block_number(
                block_hash=node_interface.get_chain_head(),
            )
            if last_block is None:  # For some reason a node can rarely return None as last block
                raise SubstrateRequestException(
                    f'{self.chain} node failed to request last block. Returned None',
                )
        except (
                requests.exceptions.RequestException,
                SubstrateRequestException,
                WebSocketException,
                ValueError,
                AttributeError,
        ) as e:
            message = (
                f'{self.chain} failed to request last block '
                f'at endpoint: {node_interface.url} due to: {e!s}.'
            )
            log.error(message)
            raise RemoteError(message) from e

        log.debug(f'{self.chain} last block', last_block=last_block)
        return BlockNumber(last_block)

    def _get_node_endpoint(self, node: NodeName) -> str:
        if node.is_owned():
            return self._format_own_rpc_endpoint(self.own_rpc_endpoint)
        return node.endpoint()

    def _get_node_interface(self, endpoint: str) -> SubstrateInterface:
        """Get an instance of SubstrateInterface, a specialized class in
        interfacing with a Substrate node that deals with SCALE encoding/decoding,
        metadata parsing, type registry management and versioning of types.

        May raise (most common):
        - RemoteError: from RequestException, problems requesting the url.
        - FileNotFound: via `load_type_registry_preset()` if it doesn't exist
        a preset file for the given `type_registry_preset` argument.
        - ValueError and TypeError: invalid constructor arguments.
        """
        try:
            node_interface = SubstrateInterface(
                url=endpoint,
                type_registry_preset=self.chain.name.lower(),
                use_remote_preset=True,
            )
        except (requests.exceptions.RequestException, WebSocketException, SubstrateRequestException) as e:  # noqa: E501
            message = (
                f'{self.chain} could not connect to node at endpoint: {endpoint}. '
                f'Connection error: {e!s}.'
            )
            log.error(message)
            raise RemoteError(message) from e
        except (FileNotFoundError, ValueError, TypeError) as e:
            message = (
                f'{self.chain} could not connect to node at endpoint: {endpoint}. '
                f'Unexpected error during SubstrateInterface instantiation: {e!s}.'
            )
            log.error(message)
            raise RemoteError('Invalid SubstrateInterface instantiation') from e

        return node_interface

    def _request_chain_metadata(self) -> dict[str, Any]:
        """Subscan API metadata documentation:
        https://docs.api.subscan.io/#metadata
        """
        url = f'https://{self.chain.name.lower()}.api.subscan.io/api/scan/metadata'
        log.debug(f'{self.chain} subscan API request', request_url=url)
        try:
            response = requests.post(url=url, timeout=CachedSettings().get_timeout_tuple())
        except requests.exceptions.RequestException as e:
            message = f'{self.chain} failed to post request at {url}. Connection error: {e!s}.'
            log.error(message)
            raise RemoteError(message) from e

        if response.status_code != HTTPStatus.OK:
            message = (
                f'{self.chain} chain metadata request was not successful. '
                f'Response status code: {response.status_code}. '
                f'Response text: {response.text}.'
            )
            log.error(message)
            raise RemoteError(message)
        try:
            result = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            message = (
                f'{self.chain} chain metadata request returned invalid JSON '
                f'response: {response.text}.'
            )
            log.error(message)
            raise RemoteError(message) from e

        log.debug(f'{self.chain} subscan API metadata', result=result)
        return result

    def _set_available_nodes_call_order(self) -> None:
        """Set `available_nodes_call_order` with a list of items (tuple of node
        and its attributes) sorted by this criteria: own node always has
        preference, then are ordered depending on how close they are to the
        chain height; the higher 'weight_block' the better.
        """
        own_node: KusamaNodeName | PolkadotNodeName
        if self.chain == SupportedBlockchain.KUSAMA:
            own_node = KusamaNodeName.OWN
        else:
            own_node = PolkadotNodeName.OWN
        node_attributes_map = self.available_node_attributes_map.copy()
        own_node_attributes = node_attributes_map.pop(own_node, None)
        available_nodes_call_order = sorted(
            cast('Iterable', node_attributes_map.items()),
            key=lambda item: -item[1].weight_block,
        )
        if own_node_attributes is not None:
            available_nodes_call_order.insert(0, (own_node, own_node_attributes))

        self.available_nodes_call_order = available_nodes_call_order

    def _set_chain_properties(self, node_interface: SubstrateInterface) -> None:
        """Return the properties of the chain connected to (e.g. native token,
        addresses format).

        May raise:
        - RemoteError: the properties request fails or there is an error
        deserializing it.
        """
        if isinstance(getattr(self, 'chain_properties', None), SubstrateChainProperties):
            log.debug(
                f'{self.chain} has already the chain properties',
                chain_properties=self.chain_properties,
            )
            return None

        self.chain_properties = self._get_chain_properties(node_interface)
        return None

    def attempt_connections(self) -> None:
        for node in self.connect_at_start:
            if node.is_owned() and len(self.own_rpc_endpoint) == 0:
                continue

            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'{self.chain} manager connection to {node} node',
                exception_is_error=True,
                method=self._connect_node,
                node=node,
                endpoint=self._get_node_endpoint(node),
            )

    @request_available_nodes
    def get_account_balance(
            self,
            account: SubstrateAddress,
            node_interface: SubstrateInterface | None = None,
    ) -> FVal:
        """Given an account get its amount of chain native token.

        May raise:
        - RemoteError: `request_available_nodes()` fails to request after
        trying with all the available nodes.
        """
        return self._get_account_balance(account=account, node_interface=node_interface)

    def get_accounts_balance(
            self,
            accounts: Sequence[SubstrateAddress],
    ) -> dict[SubstrateAddress, FVal]:
        """Given a list of accounts get their amount of chain native token.

        This method is not decorated with `request_available_nodes` on purpose,
        so each request can use all available nodes.

        May raise:
        - RemoteError: `request_available_nodes()` fails to request after
        trying with all the available nodes.
        """
        return {account: self.get_account_balance(account) for account in accounts}

    def query_balances(
            self,
            addresses: Sequence[SubstrateAddress],
    ) -> dict[SubstrateAddress, BalanceSheet]:
        usd_price = Inquirer.find_usd_price(
            asset=(asset := A_DOT if self.chain == SupportedBlockchain.POLKADOT else A_KSM),
        )

        wait_until_a_node_is_available(
            substrate_manager=self,
            seconds=SUBSTRATE_NODE_CONNECTION_TIMEOUT,
        )

        balances = {}
        account_amount = self.get_accounts_balance(addresses)
        for account, amount in account_amount.items():
            balance = Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )
            balances[account] = BalanceSheet()
            balances[account].assets[asset][DEFAULT_BALANCE_LABEL] = balance

        return balances

    @request_available_nodes
    def get_chain_id(
            self,
            node_interface: SubstrateInterface | None = None,
    ) -> SubstrateChainId:
        """
        May raise:
        - RemoteError: `request_available_nodes()` fails to request after
        trying with all the available nodes.
        """
        return self._get_chain_id(node_interface)

    @request_available_nodes
    def get_chain_properties(
            self,
            node_interface: SubstrateInterface | None = None,
    ) -> SubstrateChainProperties:
        """
        May raise:
        - RemoteError: `request_available_nodes()` fails to request after
        trying with all the available nodes.
        """
        return self._get_chain_properties(node_interface)

    @request_available_nodes
    def get_last_block(
            self,
            node_interface: SubstrateInterface | None = None,
    ) -> BlockNumber:
        """
        May raise:
        - RemoteError: `request_available_nodes()` fails to request after
        trying with all the available nodes.
        """
        return self._get_last_block(node_interface)

    def set_rpc_endpoint(self, endpoint: str) -> tuple[bool, str]:
        """Attempt to set the RPC endpoint for the user's own node.
        If connection at endpoint is successful it will set `own_rpc_endpoint`.
        """
        own_node: KusamaNodeName | PolkadotNodeName
        if self.chain == SupportedBlockchain.KUSAMA:
            own_node = KusamaNodeName.OWN
        else:
            own_node = PolkadotNodeName.OWN
        if endpoint == '':
            log.debug(f'{self.chain} removing own node at endpoint: {self.own_rpc_endpoint}')
            self.available_node_attributes_map.pop(own_node, None)
            self._set_available_nodes_call_order()
            self.own_rpc_endpoint = ''
            return True, ''

        result, message = self._connect_node(
            node=own_node,
            endpoint=self._format_own_rpc_endpoint(endpoint),
        )
        if result is True:
            self.own_rpc_endpoint = endpoint

        return result, message


def wait_until_a_node_is_available(
        substrate_manager: SubstrateManager,
        seconds: int,
) -> None:
    """Temporarily suspends the caller execution until a node is available or
    this function timeouts.
    """
    try:
        with gevent.Timeout(seconds):
            while len(substrate_manager.available_nodes_call_order) == 0:
                gevent.sleep(0.1)
    except gevent.Timeout as e:
        chain = substrate_manager.chain
        raise RemoteError(
            f'{chain} manager does not have nodes availables after waiting '
            f"{seconds} seconds. {chain} balances won't be queried.",
        ) from e
