import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, overload

from ens.abis import PUBLIC_RESOLVER_2 as ENS_RESOLVER_ABI
from ens.constants import ENS_MAINNET_ADDR
from ens.exceptions import InvalidName
from ens.utils import is_none_or_zero_address, normal_name_to_hash, normalize_name
from eth_typing import HexStr
from web3 import Web3

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.constants import (
    ARCHIVE_NODE_CHECK_ADDRESS,
    ARCHIVE_NODE_CHECK_BLOCK,
    ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
    PRUNED_NODE_CHECK_TX_HASH,
)
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.node_inquirer import (
    WEB3_LOGQUERY_BLOCK_RANGE,
    DSProxyInquirerWithCacheData,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    SupportedBlockchain,
)
from rotkehlchen.utils.misc import get_chunks

from .constants import ETH2_DEPOSIT_ADDRESS, WeightedNode

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.etherscan import Etherscan

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAX_ADDRESSES_IN_REVERSE_ENS_QUERY = 80


class EthereumInquirer(DSProxyInquirerWithCacheData):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.ETHEREUM]](chain_id=ChainID.ETHEREUM)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockchain=SupportedBlockchain.ETHEREUM,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            dsproxy_registry=contracts.contract(string_to_evm_address('0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4')),
            native_token=A_ETH.resolve_to_crypto_asset(),
            blockscout=Blockscout(
                blockchain=SupportedBlockchain.ETHEREUM,
                database=database,
                msg_aggregator=database.msg_aggregator,
            ),
        )
        self.ens_reverse_records = self.contracts.contract(string_to_evm_address('0x3671aE578E63FdF66ad4F3E12CC0c0d71Ac7510C'))  # noqa: E501
        self.blockscout: Blockscout  # for ethereum blockscout is never None since it's used for the withdrawals  # noqa: E501

    def ens_reverse_lookup(self, addresses: list[ChecksumEvmAddress]) -> dict[ChecksumEvmAddress, str | None]:  # noqa: E501
        """Performs a reverse ENS lookup on a list of addresses

        Returns a mapping of addresses to either a string name or `None`
        if there is no ens name to be found.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        - BlockchainQueryError if web3 is used and there is a VM execution error"""
        human_names: dict[ChecksumEvmAddress, str | None] = {}
        chunks = get_chunks(lst=addresses, n=MAX_ADDRESSES_IN_REVERSE_ENS_QUERY)
        for chunk in chunks:
            result = self.ens_reverse_records.call(
                node_inquirer=self,
                method_name='getNames',
                arguments=[chunk],
            )
            for addr, name in zip(chunk, result, strict=True):
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
            call_order: Sequence[WeightedNode] | None = None,
    ) -> ChecksumEvmAddress | None:
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
            call_order: Sequence[WeightedNode] | None = None,
    ) -> HexStr | None:
        ...

    def ens_lookup(
            self,
            name: str,
            blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> ChecksumEvmAddress | HexStr | None:
        return self._query(
            method=self._ens_lookup,
            call_order=call_order if call_order is not None else self.default_call_order(),
            name=name,
            blockchain=blockchain,
        )

    @overload
    def _ens_lookup(
            self,
            web3: Web3 | None,
            name: str,
            blockchain: Literal[SupportedBlockchain.ETHEREUM],
    ) -> ChecksumEvmAddress | None:
        ...

    @overload
    def _ens_lookup(
            self,
            web3: Web3 | None,
            name: str,
            blockchain: Literal[
                SupportedBlockchain.BITCOIN,
                SupportedBlockchain.KUSAMA,
                SupportedBlockchain.POLKADOT,
            ],
    ) -> HexStr | None:
        ...

    def _ens_lookup(
            self,
            web3: Web3 | None,
            name: str,
            blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
    ) -> ChecksumEvmAddress | HexStr | None:
        """Performs an ENS lookup and returns address if found else None

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
    ) -> tuple[ChecksumEvmAddress | None, str | None]:
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
                f' an ens lookup for {name}.',
            )
            return None, None

        return deserialized_resolver_addr, normal_name

    # -- Implementation of EvmNodeInquirer base methods --

    def _get_pruned_check_tx_hash(self) -> EVMTxHash:
        return PRUNED_NODE_CHECK_TX_HASH

    def _get_archive_check_data(self) -> tuple[ChecksumEvmAddress, int, FVal]:
        return (
            ARCHIVE_NODE_CHECK_ADDRESS,
            ARCHIVE_NODE_CHECK_BLOCK,
            ARCHIVE_NODE_CHECK_EXPECTED_BALANCE,
        )

    # -- Implementation of EvmNodeInquirer optional methods --

    def logquery_block_range(
            self,
            web3: Web3,
            contract_address: ChecksumEvmAddress,
    ) -> int:
        """We know that in most of its early life the Eth2 contract address returns a
        lot of results. So limit the query range to not hit the infura limits every time
        """
        infura_eth2_log_query = (
            'infura.io' in web3.manager.provider.endpoint_uri and  # type: ignore # lgtm [py/incomplete-url-substring-sanitization]
            contract_address == ETH2_DEPOSIT_ADDRESS
        )
        return WEB3_LOGQUERY_BLOCK_RANGE if infura_eth2_log_query is False else 75000
