import json
import logging
import random
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
    overload,
)
from urllib.parse import urlparse

import requests
from ens import ENS
from ens.abis import ENS as ENS_ABI, RESOLVER as ENS_RESOLVER_ABI
from ens.exceptions import InvalidName
from ens.main import ENS_MAINNET_ADDR
from ens.utils import is_none_or_zero_address, normal_name_to_hash, normalize_name
from eth_abi.exceptions import InsufficientDataBytes
from eth_typing import BlockNumber, HexStr
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
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.modules.eth2.constants import ETH2_DEPOSIT
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.ethereum.utils import multicall_2
from rotkehlchen.constants import ONE
from rotkehlchen.constants.ethereum import (
    ENS_REVERSE_RECORDS,
    ERC20TOKEN_ABI,
    ETH_SCAN,
    UNIV1_LP_ABI,
)
from rotkehlchen.errors.misc import (
    BlockchainQueryError,
    InputError,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_ethereum_address,
    deserialize_ethereum_transaction,
    deserialize_int_from_hex,
)
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EthereumTransaction,
    EVMTxHash,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, get_chunks, hex_or_bytes_to_str
from rotkehlchen.utils.network import request_get_dict

from .constants import ETHERSCAN_NODE
from .types import ETHERSCAN_NODE_NAME, NodeName, WeightedNode
from .utils import ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS

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


WEB3_LOGQUERY_BLOCK_RANGE = 250000

MAX_ADDRESSES_IN_REVERSE_ENS_QUERY = 80


def _query_web3_get_logs(
        web3: Web3,
        filter_args: FilterParams,
        from_block: int,
        to_block: Union[int, Literal['latest']],
        contract_address: ChecksumEvmAddress,
        event_name: str,
        argument_filters: Dict[str, Any],
) -> List[Dict[str, Any]]:
    until_block = web3.eth.block_number if to_block == 'latest' else to_block
    events: List[Dict[str, Any]] = []
    start_block = from_block
    # we know that in most of its early life the Eth2 contract address returns a
    # a lot of results. So limit the query range to not hit the infura limits every time
    # supress https://lgtm.com/rules/1507386916281/ since it does not apply here
    infura_eth2_log_query = (
        'infura.io' in web3.manager.provider.endpoint_uri and  # type: ignore # noqa: E501 lgtm [py/incomplete-url-substring-sanitization]
        contract_address == ETH2_DEPOSIT.address
    )
    block_range = initial_block_range = WEB3_LOGQUERY_BLOCK_RANGE
    if infura_eth2_log_query:
        block_range = initial_block_range = 75000

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


class EthereumManager():
    def __init__(
            self,
            etherscan: Etherscan,
            msg_aggregator: MessagesAggregator,
            greenlet_manager: GreenletManager,
            connect_at_start: Sequence[WeightedNode],
            database: 'DBHandler',
            eth_rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        log.debug(f'Initializing Ethereum Manager. Nodes to connect {connect_at_start}')
        self.greenlet_manager = greenlet_manager
        self.web3_mapping: Dict[NodeName, Web3] = {}
        self.etherscan = etherscan
        self.msg_aggregator = msg_aggregator
        self.eth_rpc_timeout = eth_rpc_timeout
        self.archive_connection = False
        self.queried_archive_connection = False
        self.connect_to_multiple_nodes(connect_at_start)
        self.blocks_subgraph = Graph(
            'https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks',
        )
        # A cache for the erc20 contract info to not requery same one
        self.contract_info_cache: Dict[ChecksumEvmAddress, Dict[str, Any]] = {
            # hard coding contract info we know can't be queried properly
            # https://github.com/rotki/rotki/issues/4420
            string_to_evm_address('0xECF8F87f810EcF450940c9f60066b4a7a501d6A7'): {
                'name': 'Old Wrapped Ether',
                'symbol': 'WETH',
                'decimals': 18,
            },
        }
        self.database = database

    def connected_to_any_web3(self) -> bool:
        return len(self.web3_mapping) != 0

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
        open_nodes = self.database.get_web3_nodes(only_active=True)
        selection = list(open_nodes)
        if skip_etherscan:
            selection = [wnode for wnode in open_nodes if wnode.node_info.name != ETHERSCAN_NODE_NAME]  # noqa: E501

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
                request_kwargs={'timeout': self.eth_rpc_timeout},
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
                    network_id = int(web3.net.version)

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

    def connect_to_multiple_nodes(self, nodes: Sequence[WeightedNode]) -> None:
        self.web3_mapping = {}
        for weighted_node in nodes:
            if weighted_node.node_info.name == ETHERSCAN_NODE_NAME:
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

    def query(self, method: Callable, call_order: Sequence[WeightedNode], **kwargs: Any) -> Any:
        """Queries ethereum related data by performing the provided method to all given nodes

        The first node in the call order that gets a succcesful response returns.
        If none get a result then a remote error is raised
        """
        for weighted_node in call_order:
            node = weighted_node.node_info
            web3 = self.web3_mapping.get(node, None)
            if web3 is None and node.name != ETHERSCAN_NODE_NAME:
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

    def get_historical_eth_balance(
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

    def have_archive(self, requery: bool = False) -> bool:
        """Checks to see if our own connected node is an archive node

        If requery is True it always queries the node. Otherwise it remembers last query.
        """
        if self.queried_archive_connection and requery is False:
            return self.archive_connection

        balance = self.get_historical_eth_balance(
            address=string_to_evm_address('0x50532e4Be195D1dE0c2E6DfA46D9ec0a4Fee6861'),
            block_number=87042,
        )
        self.archive_connection = balance is not None and balance == FVal('5.1063307')
        self.queried_archive_connection = True
        return self.archive_connection

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

    def get_eth_balance(self, account: ChecksumEvmAddress) -> FVal:
        """Gets the balance of the given account in ETH

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        """
        result = self.get_multieth_balance([account])
        return result[account]

    def get_multieth_balance(
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
            'Querying ethereum chain for ETH balance',
            eth_addresses=accounts,
        )
        result = ETH_SCAN.call(
            ethereum=self,
            method_name='etherBalances',
            arguments=[accounts],
            call_order=call_order if call_order is not None else self.default_call_order(),
        )
        balances = {}
        for idx, account in enumerate(accounts):
            balances[account] = from_wei(result[idx])
        return balances

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

    def ens_reverse_lookup(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, Optional[str]]:  # noqa: E501
        """Performs a reverse ENS lookup on a list of addresses

        Returns a mapping of addresses to either a string name or `None`
        if there is no ens name to be found.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        - BlockchainQueryError if web3 is used and there is a VM execution error"""
        human_names: Dict[ChecksumEvmAddress, Optional[str]] = {}
        chunks = get_chunks(lst=addresses, n=MAX_ADDRESSES_IN_REVERSE_ENS_QUERY)
        for chunk in chunks:
            result = ENS_REVERSE_RECORDS.call(
                ethereum=self,
                method_name='getNames',
                arguments=[chunk],
            )
            for addr, name in zip(chunk, result):
                if name == '':
                    human_names[addr] = None
                else:
                    human_names[addr] = name
        return human_names

    @overload
    def ens_lookup(
            self,
            name: str,
            blockchain: Literal[SupportedBlockchain.ETHEREUM] = SupportedBlockchain.ETHEREUM,
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> Optional[ChecksumEvmAddress]:
        ...

    @overload
    def ens_lookup(
            self,
            name: str,
            blockchain: Literal[
                SupportedBlockchain.BITCOIN,
                SupportedBlockchain.BITCOIN_CASH,
                SupportedBlockchain.KUSAMA,
                SupportedBlockchain.POLKADOT,
            ],
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> Optional[HexStr]:
        ...

    def ens_lookup(
            self,
            name: str,
            blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> Optional[Union[ChecksumEvmAddress, HexStr]]:
        return self.query(
            method=self._ens_lookup,
            call_order=call_order if call_order is not None else self.default_call_order(),
            name=name,
            blockchain=blockchain,
        )

    @overload
    def _ens_lookup(
            self,
            web3: Optional[Web3],
            name: str,
            blockchain: Literal[SupportedBlockchain.ETHEREUM],
    ) -> Optional[ChecksumEvmAddress]:
        ...

    @overload
    def _ens_lookup(
            self,
            web3: Optional[Web3],
            name: str,
            blockchain: Literal[
                SupportedBlockchain.BITCOIN,
                SupportedBlockchain.KUSAMA,
                SupportedBlockchain.POLKADOT,
            ],
    ) -> Optional[HexStr]:
        ...

    def _ens_lookup(
            self,
            web3: Optional[Web3],
            name: str,
            blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
    ) -> Optional[Union[ChecksumEvmAddress, HexStr]]:
        """Performs an ENS lookup and returns address if found else None

        TODO: currently web3.py 5.15.0 does not support multichain ENS domains
        (EIP-2304), therefore requesting a non-Ethereum address won't use the
        web3 ens library and will require to extend the library resolver ABI.
        An issue in their repo (#1839) reporting the lack of support has been
        created. This function will require refactoring once they include
        support for EIP-2304.
        https://github.com/ethereum/web3.py/issues/1839

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        - InputError if the given name is not a valid ENS name
        """
        try:
            normal_name = normalize_name(name)
        except InvalidName as e:
            raise InputError(str(e)) from e

        resolver_addr = self._call_contract(
            web3=web3,
            contract_address=ENS_MAINNET_ADDR,
            abi=ENS_ABI,
            method_name='resolver',
            arguments=[normal_name_to_hash(normal_name)],
        )
        if is_none_or_zero_address(resolver_addr):
            return None

        ens_resolver_abi = ENS_RESOLVER_ABI.copy()
        arguments = [normal_name_to_hash(normal_name)]
        if blockchain != SupportedBlockchain.ETHEREUM:
            ens_resolver_abi.extend(ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS)
            arguments.append(blockchain.ens_coin_type())

        try:
            deserialized_resolver_addr = deserialize_ethereum_address(resolver_addr)
        except DeserializationError:
            log.error(
                f'Error deserializing address {resolver_addr} while doing'
                f'ens lookup',
            )
            return None

        address = self._call_contract(
            web3=web3,
            contract_address=deserialized_resolver_addr,
            abi=ens_resolver_abi,
            method_name='addr',
            arguments=arguments,
        )

        if is_none_or_zero_address(address):
            return None

        if blockchain != SupportedBlockchain.ETHEREUM:
            return HexStr(address.hex())
        try:
            return deserialize_ethereum_address(address)
        except DeserializationError:
            log.error(f'Error deserializing address {address}')
            return None

    def _call_contract_etherscan(
            self,
            contract_address: ChecksumEvmAddress,
            abi: List,
            method_name: str,
            arguments: Optional[List[Any]] = None,
    ) -> Any:
        """Performs an eth_call to an ethereum contract via etherscan

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
                f'with arguments: {str(arguments)} via etherscan. Returned 0x result',
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
    ) -> EthereumTransaction:
        if web3 is None:
            tx_data = self.etherscan.get_transaction_by_hash(tx_hash=tx_hash)
        else:
            tx_data = web3.eth.get_transaction(tx_hash)  # type: ignore

        try:
            transaction = deserialize_ethereum_transaction(data=tx_data, internal=False, ethereum=self)  # noqa: E501
        except (DeserializationError, ValueError) as e:
            raise RemoteError(
                f'Couldnt deserialize ethereum transaction data from {tx_data}. Error: {str(e)}',
            ) from e

        return transaction

    def get_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            call_order: Optional[Sequence[WeightedNode]] = None,
    ) -> EthereumTransaction:
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
        """Performs an eth_call to an ethereum contract

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
            call_order = [ETHERSCAN_NODE]
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
        """Queries logs of an ethereum contract

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

                        new_events[e_idx]['address'] = deserialize_ethereum_address(
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

        WE could also add this to the get_logs() call but would add unnecessary
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

    def _get_blocknumber_by_time_from_subgraph(self, ts: Timestamp) -> int:
        """Queries Ethereum Blocks Subgraph for closest block at or before given timestamp"""
        response = self.blocks_subgraph.query(
            f"""
            {{
                blocks(
                    first: 1, orderBy: timestamp, orderDirection: desc,
                    where: {{timestamp_lte: "{ts}"}}
                ) {{
                    id
                    number
                    timestamp
                }}
            }}
            """,
        )
        try:
            result = int(response['blocks'][0]['number'])
        except (IndexError, KeyError) as e:
            raise RemoteError(
                f'Got unexpected ethereum blocks subgraph response: {response}',
            ) from e
        else:
            return result

    def get_blocknumber_by_time(self, ts: Timestamp, etherscan: bool = True) -> int:
        """Searches for the blocknumber of a specific timestamp
        - Performs the etherscan api call by default first
        - If RemoteError raised or etherscan flag set to false
            -> queries blocks subgraph
        """
        if etherscan:
            try:
                return self.etherscan.get_blocknumber_by_time(ts)
            except RemoteError:
                pass
        return self._get_blocknumber_by_time_from_subgraph(ts)

    def get_basic_contract_info(self, address: ChecksumEvmAddress) -> Dict[str, Any]:
        """
        Query a contract address and return basic information as:
        - Decimals
        - name
        - symbol
        At all times, the dictionary returned contains the keys; decimals, name & symbol.
        Although the values might be empty.

        if it is provided in the contract. This method may raise:
        - BadFunctionCallOutput: If there is an error calling a bad address
        """
        cache = self.contract_info_cache.get(address)
        if cache is not None:
            return cache

        properties = ('decimals', 'symbol', 'name')
        info: Dict[str, Any] = {}

        contract = EthereumContract(address=address, abi=ERC20TOKEN_ABI, deployed_block=0)
        try:
            # Output contains call status and result
            output = multicall_2(
                ethereum=self,
                require_success=False,
                calls=[(address, contract.encode(method_name=prop)) for prop in properties],
            )
        except RemoteError:
            # If something happens in the connection the output should have
            # the same length as the tuple of properties
            output = [(False, b'')] * len(properties)
        try:
            decoded = [
                contract.decode(x[1], method_name)[0]  # pylint: disable=E1136
                if x[0] and len(x[1]) else None
                for (x, method_name) in zip(output, properties)
            ]
        except (OverflowError, InsufficientDataBytes) as e:
            # This can happen when contract follows the ERC20 standard methods
            # but name and symbol return bytes instead of string. UNIV1 LP is such a case
            # It can also happen if the method is missing and they are all hitting
            # the fallback function. old WETH contract is such a case
            log.error(
                f'{address} failed to decode as ERC20 token. '
                f'Trying with token ABI using bytes. {str(e)}',
            )
            contract = EthereumContract(address=address, abi=UNIV1_LP_ABI, deployed_block=0)
            decoded = [
                contract.decode(x[1], method_name)[0]  # pylint: disable=E1136
                if x[0] and len(x[1]) else None
                for (x, method_name) in zip(output, properties)
            ]
            log.debug(f'{address} was succesfuly decoded as ERC20 token')

        for prop, value in zip(properties, decoded):
            if isinstance(value, bytes):
                value = value.rstrip(b'\x00').decode()
            info[prop] = value

        self.contract_info_cache[address] = info
        return info
