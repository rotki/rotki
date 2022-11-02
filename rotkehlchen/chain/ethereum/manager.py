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

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import ETHERSCAN_NODE
from rotkehlchen.chain.ethereum.modules.curve.pools_cache import (
    clear_curve_pools_cache,
    update_curve_metapools_cache,
    update_curve_registry_pools_cache,
)
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
from rotkehlchen.utils.misc import get_chunks
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.network import request_get_dict

from .types import ETHERSCAN_NODE_NAME, WeightedNode
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

    def _update_curve_decoder(self, tx_decoder: 'EVMTransactionDecoder') -> None:
        try:
            curve_decoder = tx_decoder.decoders['Curve']
        except KeyError as e:
            raise InputError(
                'Expected to find Curve decoder but it was not loaded. '
                'Please open an issue on github.com/rotki/rotki/issues if you saw this.',
            ) from e
        new_mappings = curve_decoder.reload()
        tx_decoder.address_mappings.update(new_mappings)

    @protect_with_lock()
    def curve_protocol_cache_is_queried(
            self,
            tx_decoder: Optional['EVMTransactionDecoder'],
    ) -> bool:
        """
        Make sure that information that needs to be queried is queried and if not query it.
        Returns true if the cache was modified or false otherwise.
        If the tx_decoder provided is None no information for the decoders is reloaded
        Updates curve pools cache.
        1. Deletes all previous cache values
        2. Queries information about curve pools' addresses, lp tokens and used coins
        3. Saves queried information in the cache in globaldb
        """
        if should_update_curve_cache() is False:
            if tx_decoder is not None:
                self._update_curve_decoder(tx_decoder)
            return False

        # Using shared cursor to not end up having partially populated cache
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # Delete current cache. Need to do this in case curve removes some pools
            clear_curve_pools_cache(write_cursor=write_cursor)
            # write new values to the cache
            update_curve_registry_pools_cache(
                write_cursor=write_cursor,
                ethereum_manager=self,
            )
            update_curve_metapools_cache(
                write_cursor=write_cursor,
                ethereum_manager=self,
            )

        if tx_decoder is not None:
            self._update_curve_decoder(tx_decoder)

        return True
