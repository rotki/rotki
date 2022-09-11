import json
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
)

import requests
from ens.abis import ENS as ENS_ABI, RESOLVER as ENS_RESOLVER_ABI
from ens.exceptions import InvalidName
from ens.main import ENS_MAINNET_ADDR
from ens.utils import is_none_or_zero_address, normal_name_to_hash, normalize_name
from eth_typing import BlockNumber, HexStr
from web3 import Web3
from web3.types import FilterParams

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import DEFAULT_TOKEN_DECIMALS, ETHERSCAN_NODE
from rotkehlchen.chain.ethereum.modules.curve.pools_cache import (
    clear_curve_pools_cache,
    update_curve_metapools_cache,
    update_curve_registry_pools_cache,
)
from rotkehlchen.chain.ethereum.modules.eth2.constants import ETH2_DEPOSIT
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.constants.ethereum import (
    ENS_REVERSE_RECORDS,
    ETH_MULTICALL,
    ETH_MULTICALL_2,
    ETH_SCAN,
)
from rotkehlchen.errors.misc import InputError, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_wei, get_chunks, hex_or_bytes_to_str
from rotkehlchen.utils.mixins.lockable import protect_with_lock

from .types import ETHERSCAN_NODE_NAME, NodeName, WeightedNode
from .utils import ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS, should_update_curve_cache

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


CURVE_POOLS_MAPPING_TYPE = Dict[
    ChecksumEvmAddress,  # lp token address
    Tuple[
        ChecksumEvmAddress,  # pool address
        List[ChecksumEvmAddress],  # list of coins addresses
        Optional[List[ChecksumEvmAddress]],  # optional list of underlying coins addresses
    ],
]


WEB3_LOGQUERY_BLOCK_RANGE = 250000
MAX_ADDRESSES_IN_REVERSE_ENS_QUERY = 80


class EthereumManager(EvmManager):
    """EthereumManager inherits from EvmManager and defines Ethereum-specific methods
    such as ENS resolution."""
    def __init__(
            self,
            etherscan: Etherscan,
            msg_aggregator: MessagesAggregator,
            greenlet_manager: GreenletManager,
            connect_at_start: Sequence[WeightedNode],
            database: 'DBHandler',
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        log.debug(f'Initializing Ethereum Manager. Nodes to connect {connect_at_start}')

        super().__init__(
            etherscan=etherscan,
            msg_aggregator=msg_aggregator,
            greenlet_manager=greenlet_manager,
            connect_at_start=connect_at_start,
            database=database,
            etherscan_node=ETHERSCAN_NODE,
            etherscan_node_name=ETHERSCAN_NODE_NAME,
            blockchain=SupportedBlockchain.ETHEREUM,
            contract_scan=ETH_SCAN[ChainID.ETHEREUM],
            contract_multicall=ETH_MULTICALL,
            contract_multicall_2=ETH_MULTICALL_2,
            graph_url='https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks',
            rpc_timeout=rpc_timeout,
        )
        self.contract_info_cache: Dict[ChecksumEvmAddress, Dict[str, Any]] = {
            # hard coding contract info we know can't be queried properly
            # https://github.com/rotki/rotki/issues/4420
            string_to_evm_address('0xECF8F87f810EcF450940c9f60066b4a7a501d6A7'): {
                'name': 'Old Wrapped Ether',
                'symbol': 'WETH',
                'decimals': 18,
            },
        }

    def have_archive(self, requery: bool = False) -> bool:
        if self.queried_archive_connection and requery is False:
            return self.archive_connection

        balance = self.get_historical_balance(
            address=string_to_evm_address('0x50532e4Be195D1dE0c2E6DfA46D9ec0a4Fee6861'),
            block_number=87042,
        )
        self.archive_connection = balance is not None and balance == FVal('5.1063307')
        self.queried_archive_connection = True
        return self.archive_connection

    def query_highest_block(self) -> BlockNumber:
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

    def _query_web3_get_logs(
            self,
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
            # is infura can throw an error here which we can only parse by catching the exception
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
                manager=self,
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
            deserialized_resolver_addr = deserialize_evm_address(resolver_addr)
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
            return deserialize_evm_address(address)
        except DeserializationError:
            log.error(f'Error deserializing address {address}')
            return None
