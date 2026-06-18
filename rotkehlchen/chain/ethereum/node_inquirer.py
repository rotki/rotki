import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, overload

from ens.abis import PUBLIC_RESOLVER_2 as ENS_RESOLVER_ABI, UNIVERSAL_RESOLVER
from ens.constants import UNIVERSAL_RESOLVER_ADDR
from ens.exceptions import InvalidName
from ens.utils import dns_encode_name, is_none_or_zero_address, normal_name_to_hash, normalize_name
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
from rotkehlchen.errors.misc import BlockchainQueryError, InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
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
    from rotkehlchen.externalapis.blockscout import Blockscout
    from rotkehlchen.externalapis.etherscan import Etherscan
    from rotkehlchen.externalapis.routescan import Routescan

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAX_ADDRESSES_IN_REVERSE_ENS_QUERY = 80


class EthereumInquirer(DSProxyInquirerWithCacheData):

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: 'Etherscan',
            blockscout: 'Blockscout',
            routescan: 'Routescan',
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
    ) -> None:
        contracts = EvmContracts[Literal[ChainID.ETHEREUM]](chain_id=ChainID.ETHEREUM)
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            blockscout=blockscout,
            routescan=routescan,
            blockchain=SupportedBlockchain.ETHEREUM,
            contracts=contracts,
            rpc_timeout=rpc_timeout,
            contract_multicall=contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696')),
            contract_scan=contracts.contract(BALANCE_SCANNER_ADDRESS),
            dsproxy_registry=contracts.contract(string_to_evm_address('0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4')),
            native_token=A_ETH.resolve_to_crypto_asset(),
        )

    def ens_reverse_lookup(self, addresses: list[ChecksumEvmAddress]) -> dict[ChecksumEvmAddress, str | None]:  # noqa: E501
        """Performs a reverse ENS lookup on a list of addresses

        Returns a mapping of addresses to either a string name or `None`
        if there is no ens name to be found.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        - BlockchainQueryError if web3 is used and there is a VM execution error"""
        human_names: dict[ChecksumEvmAddress, str | None] = {}
        web3 = Web3()
        universal_resolver = web3.eth.contract(abi=UNIVERSAL_RESOLVER)
        for chunk in get_chunks(lst=addresses, n=MAX_ADDRESSES_IN_REVERSE_ENS_QUERY):
            calls = [(
                UNIVERSAL_RESOLVER_ADDR,
                universal_resolver.encode_abi(
                    'reverse',
                    args=[bytes.fromhex(address.removeprefix('0x')), SupportedBlockchain.ETHEREUM.ens_coin_type()],  # noqa: E501
                ),
            ) for address in chunk]
            try:
                results = self.multicall_2(calls=calls, require_success=False)
            except RemoteError as e:
                log.error('blockchain query for ens_reverse_lookup failed due to %s', e)
                human_names.update(dict.fromkeys(chunk, None))
                continue

            for address, result in zip(chunk, results, strict=True):
                if result[0] is False or len(result[1]) == 0:
                    human_names[address] = None
                    continue

                try:
                    name, _, _ = web3.codec.decode(['string', 'address', 'address'], result[1])
                except (DeserializationError, ValueError) as e:
                    log.error(
                        'Failed to decode ens reverse lookup result for %s due to %s',
                        address,
                        e,
                    )
                    human_names[address] = None
                    continue

                human_names[address] = name or None

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
        try:
            normal_name = normalize_name(name)
        except InvalidName as e:
            raise InputError(str(e)) from e

        w3 = web3 if web3 is not None else Web3()
        resolver_contract = w3.eth.contract(abi=ENS_RESOLVER_ABI)
        node = normal_name_to_hash(normal_name)
        resolver_call = resolver_contract.encode_abi(
            'addr',
            args=[node] if blockchain == SupportedBlockchain.ETHEREUM else [node, blockchain.ens_coin_type()],  # noqa: E501
        )
        try:
            result, _ = self._call_contract(
                web3=web3,
                contract_address=UNIVERSAL_RESOLVER_ADDR,
                abi=UNIVERSAL_RESOLVER,
                method_name='resolve',
                arguments=[dns_encode_name(normal_name), resolver_call],
            )
        except (BlockchainQueryError, RemoteError) as e:
            # Universal Resolver reverts for unresolvable names. RPC nodes surface this as
            # BlockchainQueryError while indexers surface it as RemoteError. In both cases
            # the ENS lookup should behave like the old registry flow and return None.
            log.error('blockchain query for ens_lookup failed due to %s', e)
            return None

        if result in (None, b''):
            return None

        if blockchain != SupportedBlockchain.ETHEREUM:
            address = w3.codec.decode(['bytes'], result)[0]
            return None if is_none_or_zero_address(address) else HexStr(address.hex())

        address = w3.codec.decode(['address'], result)[0]
        if is_none_or_zero_address(address):
            return None

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

        try:
            resolver_addr, _, _ = self._call_contract(
                web3=None,
                contract_address=UNIVERSAL_RESOLVER_ADDR,
                abi=UNIVERSAL_RESOLVER,
                method_name='findResolver',
                arguments=[dns_encode_name(normal_name)],
            )
        except (BlockchainQueryError, RemoteError) as e:
            log.error('blockchain query for get_ens_resolver_addr failed due to %s', e)
            return None, None
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
