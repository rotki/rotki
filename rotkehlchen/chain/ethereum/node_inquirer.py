import logging
from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Literal, Optional, Union, cast, overload

import requests
from ens.abis import RESOLVER as ENS_RESOLVER_ABI
from ens.exceptions import InvalidName
from ens.main import ENS_MAINNET_ADDR
from ens.utils import is_none_or_zero_address, normal_name_to_hash, normalize_name
from eth_typing import BlockNumber, HexStr
from web3 import Web3
from web3.exceptions import TransactionNotFound

from rotkehlchen.chain.constants import DEFAULT_EVM_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    ETHEREUM_ETHERSCAN_NODE,
    PRUNED_NODE_CHECK_TX_HASH,
)
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.chain.ethereum.modules.curve.curve_cache import (
    ensure_curve_tokens_existence,
    query_curve_data,
    save_curve_data_to_cache,
)
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import WEB3_LOGQUERY_BLOCK_RANGE, EvmNodeInquirer
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import (
    BlockchainQueryError,
    InputError,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    GeneralCacheType,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import get_chunks
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock
from rotkehlchen.utils.network import request_get_dict

from .constants import ETH2_DEPOSIT_ADDRESS, ETHEREUM_ETHERSCAN_NODE_NAME, WeightedNode
from .etherscan import EthereumEtherscan
from .utils import ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS, should_update_protocol_cache

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BLOCKCYPHER_URL = 'https://api.blockcypher.com/v1/eth/main'
MAX_ADDRESSES_IN_REVERSE_ENS_QUERY = 80


class EthereumInquirer(EvmNodeInquirer, LockableQueryMixIn):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            connect_at_start: Sequence[WeightedNode],
            rpc_timeout: int = DEFAULT_EVM_RPC_TIMEOUT,
    ) -> None:
        etherscan = EthereumEtherscan(
            database=database,
            msg_aggregator=database.msg_aggregator,
        )
        LockableQueryMixIn.__init__(self)
        contracts = EvmContracts[Literal[ChainID.ETHEREUM]](chain_id=ChainID.ETHEREUM)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.ETHEREUM,
            etherscan_node=ETHEREUM_ETHERSCAN_NODE,
            etherscan_node_name=ETHEREUM_ETHERSCAN_NODE_NAME,
            contracts=contracts,
            connect_at_start=connect_at_start,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696')),  # noqa: E501
            contract_scan=contracts.contract(string_to_evm_address('0x86F25b64e1Fe4C5162cDEeD5245575D32eC549db')),  # noqa: E501
            dsproxy_registry=contracts.contract(string_to_evm_address('0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4')),  # noqa: E501
        )
        self.blocks_subgraph = Graph('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')  # noqa: E501
        self.etherscan = cast(EthereumEtherscan, self.etherscan)
        self.ens_reverse_records = self.contracts.contract(string_to_evm_address('0x3671aE578E63FdF66ad4F3E12CC0c0d71Ac7510C'))  # noqa: E501

    def ens_reverse_lookup(self, addresses: list[ChecksumEvmAddress]) -> dict[ChecksumEvmAddress, Optional[str]]:  # noqa: E501
        """Performs a reverse ENS lookup on a list of addresses

        Returns a mapping of addresses to either a string name or `None`
        if there is no ens name to be found.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        - BlockchainQueryError if web3 is used and there is a VM execution error"""
        human_names: dict[ChecksumEvmAddress, Optional[str]] = {}
        chunks = get_chunks(lst=addresses, n=MAX_ADDRESSES_IN_REVERSE_ENS_QUERY)
        for chunk in chunks:
            result = self.ens_reverse_records.call(
                node_inquirer=self,
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
        return self._query(
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
        resolver_addr, normal_name = self.get_ens_resolver_addr(name)
        if resolver_addr is None:
            log.error(f'Could not get ENS resolver for {name}')
            return None

        ens_resolver_abi = ENS_RESOLVER_ABI.copy()
        arguments = [normal_name_to_hash(normal_name)]
        if blockchain != SupportedBlockchain.ETHEREUM:
            ens_resolver_abi.extend(ENS_RESOLVER_ABI_MULTICHAIN_ADDRESS)
            arguments.append(blockchain.ens_coin_type())

        address = self._call_contract(
            web3=web3,
            contract_address=resolver_addr,
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

    def get_ens_resolver_addr(
            self,
            name: str,
    ) -> tuple[Optional[ChecksumEvmAddress], Optional[str]]:
        """Get the ENS resolver for the given name. Also returns the normalized name.

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        - InputError if the given name is not a valid ENS name
        """
        try:
            normal_name = normalize_name(name)
        except InvalidName as e:
            raise InputError(str(e)) from e

        resolver_addr = self.contracts.contract(ENS_MAINNET_ADDR).call(
            self,
            method_name='resolver',
            arguments=[normal_name_to_hash(normal_name)],
        )
        if is_none_or_zero_address(resolver_addr):
            return None, None

        try:
            deserialized_resolver_addr = deserialize_evm_address(resolver_addr)
        except DeserializationError:
            log.error(
                f'Error deserializing address {resolver_addr} while doing'
                f'ens lookup',
            )
            return None, None

        return deserialized_resolver_addr, normal_name

    @protect_with_lock()
    def assure_curve_protocol_cache_is_queried(self) -> bool:
        """
        Make sure that curve information that needs to be queried is queried and if not query it.
        Returns true if the cache was modified or false otherwise.

        1. Deletes all previous cache values
        2. Queries information about curve pools' addresses, lp tokens and used coins
        3. Saves queried information in the cache in globaldb
        """
        if should_update_protocol_cache(GeneralCacheType.CURVE_LP_TOKENS) is False:
            return False

        all_pools = query_curve_data(ethereum=self)
        if all_pools is None:
            return False
        ensure_curve_tokens_existence(ethereum_inquirer=self, all_pools=all_pools)
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            save_curve_data_to_cache(
                write_cursor=write_cursor,
                database=self.database,
                new_pools=all_pools,
            )

        return True

    # -- Implementation of EvmNodeInquirer base methods --

    def query_highest_block(self) -> BlockNumber:
        log.debug('Querying blockcypher for ETH highest block', url=BLOCKCYPHER_URL)
        eth_resp: Optional[dict[str, str]]
        try:
            eth_resp = request_get_dict(BLOCKCYPHER_URL)
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

    def _is_pruned(self, web3: Web3) -> bool:
        try:
            tx = web3.eth.get_transaction(PRUNED_NODE_CHECK_TX_HASH)  # type: ignore
        except (
            requests.exceptions.RequestException,
            TransactionNotFound,
            BlockchainQueryError,
            KeyError,
            ValueError,
        ):
            tx = None

        return tx is None

    def _have_archive(self, web3: Web3) -> bool:
        balance = self.get_historical_balance(
            address=ARCHIVE_NODE_CHECK_ADDRESS,
            block_number=ARCHIVE_NODE_CHECK_BLOCK,
            web3=web3,
        )
        return balance == ARCHIVE_NODE_CHECK_EXPECTED_BALANCE

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

    def get_blocknumber_by_time(
            self,
            ts: Timestamp,
            etherscan: bool = True,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Searches for the blocknumber of a specific timestamp
        - Performs the etherscan api call by default first
        - If RemoteError raised or etherscan flag set to false
            -> queries blocks subgraph
        """
        if etherscan:
            with suppress(RemoteError):
                return self.etherscan.get_blocknumber_by_time(ts, closest)

        return self._get_blocknumber_by_time_from_subgraph(ts)

    # -- Implementation of EvmNodeInquirer optional methods --

    def logquery_block_range(
            self,
            web3: Web3,
            contract_address: ChecksumEvmAddress,
    ) -> int:
        """We know that in most of its early life the Eth2 contract address returns a
        a lot of results. So limit the query range to not hit the infura limits every tiem
        """
        infura_eth2_log_query = (
            'infura.io' in web3.manager.provider.endpoint_uri and  # type: ignore # noqa: E501 lgtm [py/incomplete-url-substring-sanitization]
            contract_address == ETH2_DEPOSIT_ADDRESS
        )
        return WEB3_LOGQUERY_BLOCK_RANGE if infura_eth2_log_query is False else 75000
