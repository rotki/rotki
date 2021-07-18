import json
import logging
import random
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union, overload
from urllib.parse import urlparse

import requests
from ens import ENS
from ens.abis import ENS as ENS_ABI, RESOLVER as ENS_RESOLVER_ABI
from ens.exceptions import InvalidName
from ens.main import ENS_MAINNET_ADDR
from ens.utils import is_none_or_zero_address, normal_name_to_hash, normalize_name
from eth_typing import BlockNumber, HexStr
from typing_extensions import Literal
from web3 import HTTPProvider, Web3
from web3._utils.abi import get_abi_output_types
from web3._utils.contracts import find_matching_event_abi
from web3._utils.filters import construct_event_filter_params
from web3.datastructures import MutableAttributeDict
from web3.exceptions import BadFunctionCallOutput
from web3.middleware.exception_retry_request import http_retry_request_middleware
from web3.types import FilterParams

from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.modules.eth2 import ETH2_DEPOSIT
from rotkehlchen.chain.ethereum.transactions import EthTransactions
from rotkehlchen.chain.ethereum.utils import multicall_2
from rotkehlchen.constants.ethereum import ERC20TOKEN_ABI, ETH_SCAN
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import (
    BlockchainQueryError,
    DeserializationError,
    InputError,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_ethereum_address,
    deserialize_int_from_hex,
)
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.typing import ChecksumEthAddress, SupportedBlockchain, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_str
from rotkehlchen.utils.network import request_get_dict

from .typing import NodeName
from .utils import ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_ETH_RPC_TIMEOUT = 10


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


def _query_web3_get_logs(
        web3: Web3,
        filter_args: FilterParams,
        from_block: int,
        to_block: Union[int, Literal['latest']],
        contract_address: ChecksumEthAddress,
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
        except ValueError as e:
            try:
                decoded_error = json.loads(str(e).replace("'", '"'))
            except json.JSONDecodeError:
                # reraise the value error if the error is not json
                raise e from None

            msg = decoded_error.get('message', '')
            # errors from: https://infura.io/docs/ethereum/json-rpc/eth-getLogs
            if msg in ('query returned more than 10000 results', 'query timeout exceeded'):
                block_range = block_range // 2
                if block_range < 50:
                    raise  # stop retrying if block range gets too small
                # repeat the query with smaller block range
                continue
            # else, well we tried .. reraise the Value error
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


# TODO: Ideally all these should become configurable
# Taking LINKPOOL out since it's just really too slow and seems to not
# respond to the batched calls almost at all. Combined with web3.py retries
# this makes the tokens balance queries super slow.
OPEN_NODES = (
    NodeName.MYCRYPTO,
    NodeName.BLOCKSCOUT,
    NodeName.AVADO_POOL,
    NodeName.ONEINCH,
    NodeName.MYETHERWALLET,
    # NodeName.LINKPOOL,
    NodeName.CLOUDFLARE_ETH,
    NodeName.ETHERSCAN,
)
ETHEREUM_NODES_TO_CONNECT_AT_START = (
    NodeName.OWN,
    NodeName.MYCRYPTO,
    NodeName.BLOCKSCOUT,
    NodeName.ONEINCH,
    NodeName.AVADO_POOL,
    NodeName.ONEINCH,
    NodeName.MYETHERWALLET,
    # NodeName.LINKPOOL,
    NodeName.CLOUDFLARE_ETH,
)
OPEN_NODES_WEIGHT_MAP = {  # Probability with which to select each node
    NodeName.ETHERSCAN: 0.3,
    NodeName.MYCRYPTO: 0.15,
    NodeName.BLOCKSCOUT: 0.1,
    NodeName.AVADO_POOL: 0.05,
    NodeName.ONEINCH: 0.15,
    NodeName.MYETHERWALLET: 0.15,
    # NodeName.LINKPOOL: 0.05,
    NodeName.CLOUDFLARE_ETH: 0.1,
}


class EthereumManager():
    def __init__(
            self,
            ethrpc_endpoint: str,
            etherscan: Etherscan,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            greenlet_manager: GreenletManager,
            connect_at_start: Sequence[NodeName],
            eth_rpc_timeout: int = DEFAULT_ETH_RPC_TIMEOUT,
    ) -> None:
        log.debug(f'Initializing Ethereum Manager with own rpc endpoint: {ethrpc_endpoint}')
        self.greenlet_manager = greenlet_manager
        self.web3_mapping: Dict[NodeName, Web3] = {}
        self.own_rpc_endpoint = ethrpc_endpoint
        self.etherscan = etherscan
        self.msg_aggregator = msg_aggregator
        self.eth_rpc_timeout = eth_rpc_timeout
        self.transactions = EthTransactions(
            database=database,
            etherscan=etherscan,
            msg_aggregator=msg_aggregator,
        )
        for node in connect_at_start:
            self.greenlet_manager.spawn_and_track(
                after_seconds=None,
                task_name=f'Attempt connection to {str(node)} ethereum node',
                exception_is_error=True,
                method=self.attempt_connect,
                name=node,
                ethrpc_endpoint=node.endpoint(self.own_rpc_endpoint),
                mainnet_check=True,
            )
        self.blocks_subgraph = Graph(
            'https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks',
        )

    def connected_to_any_web3(self) -> bool:
        return (
            NodeName.OWN in self.web3_mapping or
            NodeName.MYCRYPTO in self.web3_mapping or
            NodeName.BLOCKSCOUT in self.web3_mapping or
            NodeName.AVADO_POOL in self.web3_mapping
        )

    def default_call_order(self, skip_etherscan: bool = False) -> List[NodeName]:
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
        result = []
        if NodeName.OWN in self.web3_mapping:
            result.append(NodeName.OWN)

        selection = list(OPEN_NODES)
        if skip_etherscan:
            selection.remove(NodeName.ETHERSCAN)

        ordered_list = []
        while len(selection) != 0:
            weights = []
            for entry in selection:
                weights.append(OPEN_NODES_WEIGHT_MAP[entry])
            node = random.choices(selection, weights, k=1)
            ordered_list.append(node[0])
            selection.remove(node[0])

        return result + ordered_list

    def attempt_connect(
            self,
            name: NodeName,
            ethrpc_endpoint: str,
            mainnet_check: bool = True,
    ) -> Tuple[bool, str]:
        """Attempt to connect to a particular node type

        For our own node if the given rpc endpoint is not the same as the saved one
        the connection is re-attempted to the new one
        """
        message = ''
        node_connected = self.web3_mapping.get(name, None) is not None
        own_node_already_connected = (
            name == NodeName.OWN and
            self.own_rpc_endpoint == ethrpc_endpoint and
            node_connected
        )
        if own_node_already_connected or (node_connected and name != NodeName.OWN):
            return True, 'Already connected to an ethereum node'

        try:
            parsed_eth_rpc_endpoint = urlparse(ethrpc_endpoint)
            if not parsed_eth_rpc_endpoint.scheme:
                ethrpc_endpoint = f"http://{ethrpc_endpoint}"
            provider = HTTPProvider(
                endpoint_uri=ethrpc_endpoint,
                request_kwargs={'timeout': self.eth_rpc_timeout},
            )
            ens = ENS(provider)
            web3 = Web3(provider, ens=ens)
            web3.middleware_onion.inject(http_retry_request_middleware, layer=0)
        except requests.exceptions.RequestException:
            message = f'Failed to connect to ethereum node {name} at endpoint {ethrpc_endpoint}'
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
                            f'Connected to ethereum node {name} at endpoint {ethrpc_endpoint} but '
                            f'it is not on the ethereum mainnet. The chain id '
                            f'the node is in is {network_id}.'
                        )
                        log.warning(message)
                        return False, message

                    current_block = web3.eth.block_number  # pylint: disable=no-member
                    try:
                        latest_block = self.query_eth_highest_block()
                    except RemoteError:
                        msg = 'Could not query latest block'
                        log.warning(msg)
                        synchronized = False
                    else:
                        synchronized, msg = _is_synchronized(current_block, latest_block)
            except ValueError as e:
                message = (
                    f'Failed to connect to ethereum node {name} at endpoint '
                    f'{ethrpc_endpoint} due to {str(e)}'
                )
                return False, message

            if not synchronized:
                self.msg_aggregator.add_warning(
                    f'We could not verify that ethereum node {name} is '
                    'synchronized with the ethereum mainnet. Balances and other queries '
                    'may be incorrect.',
                )

            log.info(f'Connected ethereum node {name} at {ethrpc_endpoint}')
            self.web3_mapping[name] = web3
            return True, ''

        # else
        message = f'Failed to connect to ethereum node {name} at endpoint {ethrpc_endpoint}'
        log.warning(message)
        return False, message

    def set_rpc_endpoint(self, endpoint: str) -> Tuple[bool, str]:
        """ Attempts to set the RPC endpoint for the user's own ethereum node

           Returns a tuple (result, message)
               - result: Boolean for success or failure of changing the rpc endpoint
               - message: A message containing information on what happened. Can
                          be populated both in case of success or failure"""
        if endpoint == '':
            self.web3_mapping.pop(NodeName.OWN, None)
            self.own_rpc_endpoint = ''
            return True, ''

        # else
        result, message = self.attempt_connect(name=NodeName.OWN, ethrpc_endpoint=endpoint)
        if result:
            log.info('Setting own node ETH RPC endpoint', endpoint=endpoint)
            self.own_rpc_endpoint = endpoint
        return result, message

    def query(self, method: Callable, call_order: Sequence[NodeName], **kwargs: Any) -> Any:
        """Queries ethereum related data by performing the provided method to all given nodes

        The first node in the call order that gets a succcesful response returns.
        If none get a result then a remote error is raised
        """
        for node in call_order:
            web3 = self.web3_mapping.get(node, None)
            if web3 is None and node != NodeName.ETHERSCAN:
                continue

            try:
                result = method(web3, **kwargs)
            except (RemoteError, BlockchainQueryError, requests.exceptions.RequestException) as e:
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

    def get_latest_block_number(self, call_order: Optional[Sequence[NodeName]] = None) -> int:
        return self.query(
            method=self._get_latest_block_number,
            call_order=call_order if call_order is not None else self.default_call_order(),
        )

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

    def get_eth_balance(self, account: ChecksumEthAddress) -> FVal:
        """Gets the balance of the given account in ETH

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        """
        result = self.get_multieth_balance([account])
        return result[account]

    def get_multieth_balance(
            self,
            accounts: List[ChecksumEthAddress],
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> Dict[ChecksumEthAddress, FVal]:
        """Returns a dict with keys being accounts and balances in ETH

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        balances: Dict[ChecksumEthAddress, FVal] = {}
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
            call_order: Optional[Sequence[NodeName]] = None,
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
        """
        if web3 is None:
            return self.etherscan.get_block_by_number(num)

        block_data: MutableAttributeDict = MutableAttributeDict(web3.eth.get_block(num))  # type: ignore # pylint: disable=no-member  # noqa: E501
        block_data['hash'] = hex_or_bytes_to_str(block_data['hash'])
        return dict(block_data)

    def get_code(
            self,
            account: ChecksumEthAddress,
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> str:
        return self.query(
            method=self._get_code,
            call_order=call_order if call_order is not None else self.default_call_order(),
            account=account,
        )

    def _get_code(self, web3: Optional[Web3], account: ChecksumEthAddress) -> str:
        """Gets the deployment bytecode at the given address

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        """
        if web3 is None:
            return self.etherscan.get_code(account)

        return hex_or_bytes_to_str(web3.eth.getCode(account))

    @overload
    def ens_lookup(
            self,
            name: str,
            blockchain: Literal[SupportedBlockchain.ETHEREUM] = SupportedBlockchain.ETHEREUM,
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> Optional[ChecksumEthAddress]:
        ...

    @overload
    def ens_lookup(
            self,
            name: str,
            blockchain: Literal[
                SupportedBlockchain.BITCOIN,
                SupportedBlockchain.KUSAMA,
            ],
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> Optional[HexStr]:
        ...

    def ens_lookup(
            self,
            name: str,
            blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> Optional[Union[ChecksumEthAddress, HexStr]]:
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
    ) -> Optional[ChecksumEthAddress]:
        ...

    @overload
    def _ens_lookup(
            self,
            web3: Optional[Web3],
            name: str,
            blockchain: Literal[
                SupportedBlockchain.BITCOIN,
                SupportedBlockchain.KUSAMA,
            ],
    ) -> Optional[HexStr]:
        ...

    def _ens_lookup(
            self,
            web3: Optional[Web3],
            name: str,
            blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
    ) -> Optional[Union[ChecksumEthAddress, HexStr]]:
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
            contract_address: ChecksumEthAddress,
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
            tx_hash: str,
    ) -> Dict[str, Any]:
        if web3 is None:
            tx_receipt = self.etherscan.get_transaction_receipt(tx_hash)
            try:
                # Turn hex numbers to int
                block_number = int(tx_receipt['blockNumber'], 16)
                tx_receipt['blockNumber'] = block_number
                tx_receipt['cumulativeGasUsed'] = int(tx_receipt['cumulativeGasUsed'], 16)
                tx_receipt['gasUsed'] = int(tx_receipt['gasUsed'], 16)
                tx_receipt['status'] = int(tx_receipt['status'], 16)
                tx_index = int(tx_receipt['transactionIndex'], 16)
                tx_receipt['transactionIndex'] = tx_index
                for receipt_log in tx_receipt['logs']:
                    receipt_log['blockNumber'] = block_number
                    receipt_log['logIndex'] = deserialize_int_from_hex(
                        symbol=receipt_log['logIndex'],
                        location='etherscan tx receipt',
                    )
                    receipt_log['transactionIndex'] = tx_index
            except (DeserializationError, ValueError) as e:
                raise RemoteError(
                    f'Couldnt deserialize transaction receipt data from etherscan {tx_receipt}',
                ) from e
            return tx_receipt

        tx_receipt = web3.eth.get_transaction_receipt(tx_hash)  # type: ignore
        return process_result(tx_receipt)

    def get_transaction_receipt(
            self,
            tx_hash: str,
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> Dict[str, Any]:
        return self.query(
            method=self._get_transaction_receipt,
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
        )

    def call_contract(
            self,
            contract_address: ChecksumEthAddress,
            abi: List,
            method_name: str,
            arguments: Optional[List[Any]] = None,
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> Any:
        return self.query(
            method=self._call_contract,
            call_order=call_order if call_order is not None else self.default_call_order(),
            contract_address=contract_address,
            abi=abi,
            method_name=method_name,
            arguments=arguments,
        )

    def _call_contract(
            self,
            web3: Optional[Web3],
            contract_address: ChecksumEthAddress,
            abi: List,
            method_name: str,
            arguments: Optional[List[Any]] = None,
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
            method = getattr(contract.caller, method_name)
            result = method(*arguments if arguments else [])
        except (ValueError, BadFunctionCallOutput) as e:
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address}: {str(e)}',
            ) from e
        return result

    def get_logs(
            self,
            contract_address: ChecksumEthAddress,
            abi: List,
            event_name: str,
            argument_filters: Dict[str, Any],
            from_block: int,
            to_block: Union[int, Literal['latest']] = 'latest',
            call_order: Optional[Sequence[NodeName]] = None,
    ) -> List[Dict[str, Any]]:
        if call_order is None:  # Default call order for logs
            call_order = (NodeName.OWN, NodeName.ETHERSCAN)
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
            contract_address: ChecksumEthAddress,
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

    def get_basic_contract_info(self, address: ChecksumEthAddress) -> Dict[str, Any]:
        """
        Query a contract address and return basic information as:
        - Decimals
        - name
        - symbol
        if it is provided in the contract. This method may raise:
        - BadFunctionCallOutput: If there is an error calling a bad address
        """
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

        decoded = [
            contract.decode(x[1], method_name)[0]  # pylint: disable=E1136
            if x[0] and len(x[1]) else None
            for (x, method_name) in zip(output, properties)
        ]

        for prop, value in zip(properties, decoded):
            info[prop] = value

        return info
