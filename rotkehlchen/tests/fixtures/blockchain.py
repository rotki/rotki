from collections.abc import Sequence
from contextlib import ExitStack
from typing import Literal
from unittest.mock import patch

import pytest

from rotkehlchen.chain.accounts import BlockchainAccounts
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
from rotkehlchen.chain.arbitrum_one.transactions import ArbitrumOneTransactions
from rotkehlchen.chain.avalanche.manager import AvalancheManager
from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
from rotkehlchen.chain.base.manager import BaseManager
from rotkehlchen.chain.base.node_inquirer import BaseInquirer
from rotkehlchen.chain.base.transactions import BaseTransactions
from rotkehlchen.chain.binance_sc.manager import BinanceSCManager
from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
from rotkehlchen.chain.bitcoin.bch.manager import BitcoinCashManager
from rotkehlchen.chain.bitcoin.btc.manager import BitcoinManager
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.gnosis.manager import GnosisManager
from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
from rotkehlchen.chain.gnosis.transactions import GnosisTransactions
from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
from rotkehlchen.chain.optimism.manager import OptimismManager
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.chain.optimism.transactions import OptimismTransactions
from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
from rotkehlchen.chain.scroll.manager import ScrollManager
from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
from rotkehlchen.chain.solana.manager import SolanaManager
from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
from rotkehlchen.chain.substrate.manager import SubstrateChainProperties, SubstrateManager
from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.chain.zksync_lite.manager import ZksyncLiteManager
from rotkehlchen.constants.assets import A_DOT, A_KSM
from rotkehlchen.db.settings import DEFAULT_BTC_DERIVATION_GAP_LIMIT
from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.externalapis.helius import Helius
from rotkehlchen.externalapis.opensea import Opensea
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.blockchain import maybe_modify_rpc_nodes
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.evm import maybe_mock_evm_inquirer
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import mock_proxies, patch_etherscan_request
from rotkehlchen.tests.utils.solana import patch_solana_inquirer_nodes
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_DEFAULT_OWN_RPC_ENDPOINT,
    KUSAMA_MAIN_ASSET_DECIMALS,
    KUSAMA_SS58_FORMAT,
    POLKADOT_SS58_FORMAT,
    wait_until_all_substrate_nodes_connected,
)
from rotkehlchen.types import BTCAddress, ChecksumEvmAddress, SolanaAddress, SupportedBlockchain


def _initialize_and_yield_evm_inquirer_fixture(
        parent_stack,
        klass,
        class_path,
        manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
        mock_data,
        mocked_proxies,
):
    blockchain = SupportedBlockchain.ETHEREUM
    if klass == OptimismInquirer:
        blockchain = SupportedBlockchain.OPTIMISM
    elif klass == PolygonPOSInquirer:
        blockchain = SupportedBlockchain.POLYGON_POS
    elif klass == ArbitrumOneInquirer:
        blockchain = SupportedBlockchain.ARBITRUM_ONE
    elif klass == BaseInquirer:
        blockchain = SupportedBlockchain.BASE
    elif klass == GnosisInquirer:
        blockchain = SupportedBlockchain.GNOSIS
    elif klass == ScrollInquirer:
        blockchain = SupportedBlockchain.SCROLL
    elif klass == BinanceSCInquirer:
        blockchain = SupportedBlockchain.BINANCE_SC

    EvmContracts.initialize_common_abis()
    nodes_to_connect_to = maybe_modify_rpc_nodes(database, blockchain, manager_connect_at_start)

    with ExitStack() as init_stack:
        if mock_other_web3 is True:
            init_stack.enter_context(patch(  # at init of Inquirer attempt no connection if mocking
                class_path,
                return_value=lambda *args: None,
            ))
        inquirer = klass(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=(etherscan := Etherscan(
                database=database,
                msg_aggregator=database.msg_aggregator,
            )),
        )

    if mock_other_web3:  # this allows only to match on ethereum only. To allow other chains we need to improve the logic since etherscan is the same object for all the chains  # noqa: E501
        parent_stack.enter_context(patch_etherscan_request(
            etherscan=etherscan,
            mock_data=mock_data,
        ))

    maybe_mock_evm_inquirer(
        should_mock=mock_other_web3,
        parent_stack=parent_stack,
        evm_inquirer=inquirer,
        manager_connect_at_start=nodes_to_connect_to,
        mock_data=mock_data,
    )
    if mocked_proxies is not None:
        mock_proxies(parent_stack, mocked_proxies)
    return inquirer


@pytest.fixture(name='number_of_eth_accounts')
def fixture_number_of_eth_accounts():
    return 4


@pytest.fixture(name='ethereum_accounts')
def fixture_ethereum_accounts(number_of_eth_accounts) -> list[ChecksumEvmAddress]:
    return [make_evm_address() for x in range(number_of_eth_accounts)]


@pytest.fixture(name='optimism_accounts')
def fixture_optimism_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='polygon_pos_accounts')
def fixture_polygon_pos_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='arbitrum_one_accounts')
def fixture_arbitrum_one_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='base_accounts')
def fixture_base_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='gnosis_accounts')
def fixture_gnosis_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='scroll_accounts')
def fixture_scroll_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='binance_sc_accounts')
def fixture_binance_sc_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='zksync_lite_accounts')
def fixture_zksync_lite_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='btc_accounts')
def fixture_btc_accounts() -> list[BTCAddress]:
    return []


@pytest.fixture(name='bch_accounts')
def fixture_bch_accounts() -> list[BTCAddress]:
    return []


@pytest.fixture(name='solana_accounts')
def fixture_solana_accounts() -> list[SolanaAddress]:
    return []


@pytest.fixture(name='ksm_accounts')
def fixture_ksm_accounts() -> list[SubstrateAddress]:
    """As per feature requirements, instantiating SubstrateManager won't trigger
    the logic that attempts to connect to the nodes. Use this fixture with KSM
    addresses on tests (e.g. integration/API tests) that require connection
    since instantiation.
    """
    return []


@pytest.fixture(name='dot_accounts')
def fixture_dot_accounts() -> list[SubstrateAddress]:
    """As per feature requirements, instantiating SubstrateManager won't trigger
    the logic that attempts to connect to the nodes. Use this fixture with KSM
    addresses on tests (e.g. integration/API tests) that require connection
    since instantiation.
    """
    return []


@pytest.fixture(name='avax_accounts')
def fixture_avax_accounts() -> list[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='blockchain_accounts')
def fixture_blockchain_accounts(
        ethereum_accounts: list[ChecksumEvmAddress],
        optimism_accounts: list[ChecksumEvmAddress],
        polygon_pos_accounts: list[ChecksumEvmAddress],
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        base_accounts: list[ChecksumEvmAddress],
        gnosis_accounts: list[ChecksumEvmAddress],
        scroll_accounts: list[ChecksumEvmAddress],
        binance_sc_accounts: list[ChecksumEvmAddress],
        zksync_lite_accounts: list[ChecksumEvmAddress],
        avax_accounts: list[ChecksumEvmAddress],
        btc_accounts: list[BTCAddress],
        bch_accounts: list[BTCAddress],
        ksm_accounts: list[SubstrateAddress],
        dot_accounts: list[SubstrateAddress],
        solana_accounts: list[SolanaAddress],
) -> BlockchainAccounts:
    return BlockchainAccounts(
        eth=tuple(ethereum_accounts),
        optimism=tuple(optimism_accounts),
        polygon_pos=tuple(polygon_pos_accounts),
        arbitrum_one=tuple(arbitrum_one_accounts),
        base=tuple(base_accounts),
        gnosis=tuple(gnosis_accounts),
        scroll=tuple(scroll_accounts),
        binance_sc=tuple(binance_sc_accounts),
        zksync_lite=tuple(zksync_lite_accounts),
        avax=tuple(avax_accounts),
        btc=tuple(btc_accounts),
        bch=tuple(bch_accounts),
        ksm=tuple(ksm_accounts),
        dot=tuple(dot_accounts),
        solana=tuple(solana_accounts),
    )


@pytest.fixture(name='ethrpc_endpoint')
def fixture_ethrpc_endpoint() -> str | None:
    return None


@pytest.fixture(name='ethereum_manager_connect_at_start')
def fixture_ethereum_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.

    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='should_mock_web3')
def fixture_should_mock_web3() -> bool:
    """A fixture to specify if web3 should be mocked. Should be set at tests"""
    return False


@pytest.fixture(name='ethereum_mock_data')
def fixture_ethereum_mock_data():
    """Can contain mocked data for both etherscan and web3 requests"""
    return {}


@pytest.fixture(name='optimism_mock_data')
def fixture_optimism_mock_data():
    """Can contain mocked data for both etherscan and web3 requests"""
    return {}


@pytest.fixture(name='mock_other_web3')
def fixture_mock_other_web3(network_mocking, should_mock_web3):
    """Just like fixture_web3_mocking this decides but in boolean
    without yielding if web3 and related stuff should be mocked"""
    if network_mocking is False:
        return False
    return should_mock_web3


@pytest.fixture(name='ethereum_inquirer')
def fixture_ethereum_inquirer(
        ethereum_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
        ethereum_mock_data,
        mocked_proxies,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=EthereumInquirer,
            class_path='rotkehlchen.chain.ethereum.node_inquirer.EthereumInquirer',
            manager_connect_at_start=ethereum_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data=ethereum_mock_data,
            mocked_proxies=mocked_proxies,
        )


@pytest.fixture(name='ethereum_manager')
def fixture_ethereum_manager(ethereum_inquirer):
    return EthereumManager(node_inquirer=ethereum_inquirer)


@pytest.fixture(name='ethereum_transaction_decoder')
def fixture_ethereum_transaction_decoder(
        database,
        ethereum_inquirer,
        eth_transactions,
        load_global_caches,
):
    with patch_decoder_reload_data(load_global_caches):
        yield EthereumTransactionDecoder(
            database=database,
            ethereum_inquirer=ethereum_inquirer,
            transactions=eth_transactions,
        )


@pytest.fixture(name='have_decoders')
def fixture_have_decoders() -> bool:
    """If false, then no decoders will be initialized by the test fixtures.
    This saves us test time at initialization"""
    return False


@pytest.fixture(name='eth_transactions')
def fixture_eth_transactions(database, ethereum_inquirer):
    return EthereumTransactions(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
    )


@pytest.fixture(name='optimism_manager_connect_at_start')
def fixture_optimism_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.

    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='optimism_inquirer')
def fixture_optimism_inquirer(
        optimism_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
        optimism_mock_data,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=OptimismInquirer,
            class_path='rotkehlchen.chain.optimism.node_inquirer.OptimismInquirer',
            manager_connect_at_start=optimism_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data=optimism_mock_data,
            mocked_proxies=None,
        )


@pytest.fixture(name='optimism_manager')
def fixture_optimism_manager(optimism_inquirer):
    return OptimismManager(node_inquirer=optimism_inquirer)


@pytest.fixture(name='optimism_transactions')
def fixture_optimism_transactions(database, optimism_inquirer):
    return OptimismTransactions(
        optimism_inquirer=optimism_inquirer,
        database=database,
    )


@pytest.fixture(name='arbitrum_one_transactions')
def fixture_arbitrum_one_transactions(database, arbitrum_one_inquirer):
    return ArbitrumOneTransactions(
        arbitrum_one_inquirer=arbitrum_one_inquirer,
        database=database,
    )


@pytest.fixture(name='base_transactions')
def fixture_base_transactions(database, base_inquirer):
    return BaseTransactions(
        base_inquirer=base_inquirer,
        database=database,
    )


@pytest.fixture(name='optimism_transaction_decoder')
def fixture_optimism_transaction_decoder(
        database,
        optimism_inquirer,
        optimism_transactions,
        load_global_caches,
):
    with patch_decoder_reload_data(load_global_caches):
        yield OptimismTransactionDecoder(
            database=database,
            optimism_inquirer=optimism_inquirer,
            transactions=optimism_transactions,
        )


@pytest.fixture(name='base_transaction_decoder')
def fixture_base_transaction_decoder(
        database,
        base_inquirer,
        base_transactions,
        load_global_caches,
):
    with patch_decoder_reload_data(load_global_caches):
        yield BaseTransactionDecoder(
            database=database,
            base_inquirer=base_inquirer,
            transactions=base_transactions,
        )


@pytest.fixture(name='arbitrum_one_transaction_decoder')
def fixture_arbitrum_one_transaction_decoder(
        database,
        arbitrum_one_inquirer,
        arbitrum_one_transactions,
        load_global_caches,
):
    with patch_decoder_reload_data(load_global_caches):
        yield ArbitrumOneTransactionDecoder(
            database=database,
            arbitrum_inquirer=arbitrum_one_inquirer,
            transactions=arbitrum_one_transactions,
        )


@pytest.fixture(name='polygon_pos_manager_connect_at_start')
def fixture_polygon_pos_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.

    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='polygon_pos_inquirer')
def fixture_polygon_pos_inquirer(
        polygon_pos_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=PolygonPOSInquirer,
            class_path='rotkehlchen.chain.polygon_pos.node_inquirer.PolygonPOSInquirer',
            manager_connect_at_start=polygon_pos_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data={},  # Not used in polygon. TODO: remove it for all other chains too since we now have vcr  # noqa: E501
            mocked_proxies=None,
        )


@pytest.fixture(name='polygon_pos_manager')
def fixture_polygon_pos_manager(polygon_pos_inquirer):
    return PolygonPOSManager(node_inquirer=polygon_pos_inquirer)


@pytest.fixture(name='arbitrum_one_manager_connect_at_start')
def fixture_arbitrum_one_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.

    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='arbitrum_one_inquirer')
def fixture_arbitrum_one_inquirer(
        arbitrum_one_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=ArbitrumOneInquirer,
            class_path='rotkehlchen.chain.arbitrum_one.node_inquirer.ArbitrumOneInquirer',
            manager_connect_at_start=arbitrum_one_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data={},  # Not used in arbitrum. TODO: remove it for all other chains too since we now have vcr  # noqa: E501
            mocked_proxies=None,
        )


@pytest.fixture(name='arbitrum_one_manager')
def fixture_arbitrum_one_manager(arbitrum_one_inquirer):
    return ArbitrumOneManager(node_inquirer=arbitrum_one_inquirer)


@pytest.fixture(name='base_manager_connect_at_start')
def fixture_base_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.
    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='base_inquirer')
def fixture_base_inquirer(
        base_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=BaseInquirer,
            class_path='rotkehlchen.chain.base.node_inquirer.BaseInquirer',
            manager_connect_at_start=base_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data={},  # Not used in base. TODO: remove it for all other chains too since we now have vcr  # noqa: E501
            mocked_proxies=None,
        )


@pytest.fixture(name='base_manager')
def fixture_base_manager(base_inquirer):
    return BaseManager(node_inquirer=base_inquirer)


@pytest.fixture(name='gnosis_manager_connect_at_start')
def fixture_gnosis_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.
    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='gnosis_inquirer')
def fixture_gnosis_inquirer(
        gnosis_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=GnosisInquirer,
            class_path='rotkehlchen.chain.gnosis.node_inquirer.GnosisInquirer',
            manager_connect_at_start=gnosis_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data={},  # Not used in gnosis. TODO: remove it for all other chains too since we now have vcr  # noqa: E501
            mocked_proxies=None,
        )


@pytest.fixture(name='gnosis_manager')
def fixture_gnosis_manager(gnosis_inquirer):
    return GnosisManager(node_inquirer=gnosis_inquirer)


@pytest.fixture(name='gnosis_transactions')
def fixture_gnosis_transactions(
        database,
        gnosis_inquirer,
):
    return GnosisTransactions(
        gnosis_inquirer=gnosis_inquirer,
        database=database,
    )


@pytest.fixture(name='scroll_manager_connect_at_start')
def fixture_scroll_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.
    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='scroll_inquirer')
def fixture_scroll_inquirer(
        scroll_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=ScrollInquirer,
            class_path='rotkehlchen.chain.scroll.node_inquirer.ScrollInquirer',
            manager_connect_at_start=scroll_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data={},  # Not used in scroll. TODO: remove it for all other chains too since we now have vcr  # noqa: E501
            mocked_proxies=None,
        )


@pytest.fixture(name='scroll_manager')
def fixture_scroll_manager(scroll_inquirer):
    return ScrollManager(node_inquirer=scroll_inquirer)


@pytest.fixture(name='binance_sc_manager_connect_at_start')
def fixture_binance_sc_manager_connect_at_start() -> Literal['DEFAULT'] | Sequence[NodeName]:
    """A sequence of nodes to connect to at the start of the test.
    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return ()


@pytest.fixture(name='binance_sc_inquirer')
def fixture_binance_sc_inquirer(
        binance_sc_manager_connect_at_start,
        greenlet_manager,
        database,
        mock_other_web3,
):
    with ExitStack() as stack:
        yield _initialize_and_yield_evm_inquirer_fixture(
            parent_stack=stack,
            klass=BinanceSCInquirer,
            class_path='rotkehlchen.chain.binance_sc.node_inquirer.BinanceSCInquirer',
            manager_connect_at_start=binance_sc_manager_connect_at_start,
            greenlet_manager=greenlet_manager,
            database=database,
            mock_other_web3=mock_other_web3,
            mock_data={},  # Not used in bsc. TODO: remove it for all other chains too since we now have vcr  # noqa: E501
            mocked_proxies=None,
        )


@pytest.fixture(name='binance_sc_manager')
def fixture_binance_sc_manager(binance_sc_inquirer):
    return BinanceSCManager(node_inquirer=binance_sc_inquirer)


@pytest.fixture(name='ksm_rpc_endpoint')
def fixture_ksm_rpc_endpoint() -> str | None:
    return None


@pytest.fixture(name='dot_rpc_endpoint')
def fixture_dot_rpc_endpoint() -> str | None:
    return None


@pytest.fixture(name='kusama_manager_connect_at_start')
def fixture_kusama_manager_connect_at_start() -> Sequence[NodeName]:
    return ()


@pytest.fixture(name='polkadot_manager_connect_at_start')
def fixture_polkadot_manager_connect_at_start() -> Sequence[NodeName]:
    return ()


@pytest.fixture(name='kusama_available_node_attributes_map')
def fixture_kusama_available_node_attributes_map():
    return {}


@pytest.fixture(name='polkadot_available_node_attributes_map')
def fixture_polkadot_available_node_attributes_map():
    return {}


def _make_substrate_manager(
        messages_aggregator,
        greenlet_manager,
        accounts,
        chain_type,
        rpc_endpoint,
        available_node_attributes_map,
        connect_at_start,
):
    own_rpc_endpoint = (
        rpc_endpoint if rpc_endpoint is not None else KUSAMA_DEFAULT_OWN_RPC_ENDPOINT
    )
    substrate_manager = SubstrateManager(
        chain=chain_type,
        msg_aggregator=messages_aggregator,
        greenlet_manager=greenlet_manager,
        connect_at_start=connect_at_start,
        connect_on_startup=bool(accounts),
        own_rpc_endpoint=own_rpc_endpoint,
    )
    if len(available_node_attributes_map) != 0:
        # When connection is persisted <SubstrateManager.chain_properties> must
        # be set manually (either requesting the chain or hard coded)
        substrate_manager.available_node_attributes_map = available_node_attributes_map
        substrate_manager._set_available_nodes_call_order()
        # NB: for speeding up tests, instead of requesting the properties of
        # the chain, we manually set them.
        if chain_type == SupportedBlockchain.KUSAMA:
            substrate_manager.chain_properties = SubstrateChainProperties(
                ss58_format=KUSAMA_SS58_FORMAT,
                token=A_KSM,
                token_decimals=KUSAMA_MAIN_ASSET_DECIMALS,
            )
        else:
            substrate_manager.chain_properties = SubstrateChainProperties(
                ss58_format=POLKADOT_SS58_FORMAT,
                token=A_DOT,
                token_decimals=10,
            )

    else:
        wait_until_all_substrate_nodes_connected(
            substrate_manager_connect_at_start=connect_at_start,
            substrate_manager=substrate_manager,
        )

    return substrate_manager


@pytest.fixture(name='kusama_manager')
def fixture_kusama_manager(
        messages_aggregator,
        greenlet_manager,
        ksm_accounts,
        ksm_rpc_endpoint,
        kusama_available_node_attributes_map,
        kusama_manager_connect_at_start,
):
    return _make_substrate_manager(
        messages_aggregator=messages_aggregator,
        greenlet_manager=greenlet_manager,
        accounts=ksm_accounts,
        chain_type=SupportedBlockchain.KUSAMA,
        rpc_endpoint=ksm_rpc_endpoint,
        available_node_attributes_map=kusama_available_node_attributes_map,
        connect_at_start=kusama_manager_connect_at_start,
    )


@pytest.fixture(name='polkadot_manager')
def fixture_polkadot_manager(
        messages_aggregator,
        greenlet_manager,
        dot_accounts,
        dot_rpc_endpoint,
        polkadot_available_node_attributes_map,
        polkadot_manager_connect_at_start,
):
    return _make_substrate_manager(
        messages_aggregator=messages_aggregator,
        greenlet_manager=greenlet_manager,
        accounts=dot_accounts,
        chain_type=SupportedBlockchain.POLKADOT,
        rpc_endpoint=dot_rpc_endpoint,
        available_node_attributes_map=polkadot_available_node_attributes_map,
        connect_at_start=polkadot_manager_connect_at_start,
    )


@pytest.fixture(name='avalanche_manager')
def fixture_avalanche_manager(messages_aggregator):
    return AvalancheManager(
        avaxrpc_endpoint='https://api.avax.network/ext/bc/C/rpc',
        msg_aggregator=messages_aggregator,
    )


@pytest.fixture(name='zksync_lite_manager')
def fixture_zksync_lite_manager(ethereum_inquirer, database):
    return ZksyncLiteManager(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
    )


@pytest.fixture(name='bitcoin_manager')
def fixture_bitcoin_manager(database):
    return BitcoinManager(database=database)


@pytest.fixture(name='bitcoin_cash_manager')
def fixture_bitcoin_cash_manager(database):
    return BitcoinCashManager(database=database)


@pytest.fixture(name='ethereum_modules')
def fixture_ethereum_modules() -> list[str]:
    return []


@pytest.fixture(name='beaconchain')
def fixture_beaconchain(database, messages_aggregator):
    return BeaconChain(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture(name='opensea')
def fixture_opensea(database, messages_aggregator, ethereum_inquirer):
    return Opensea(
        database=database,
        msg_aggregator=messages_aggregator,
        ethereum_inquirer=ethereum_inquirer,
    )


@pytest.fixture(name='btc_derivation_gap_limit')
def fixture_btc_derivation_gap_limit():
    return DEFAULT_BTC_DERIVATION_GAP_LIMIT


@pytest.fixture(name='solana_nodes_connect_at_start')
def fixture_solana_nodes_connect_at_start() -> Literal['DEFAULT'] | Sequence[WeightedNode]:
    """A sequence of nodes to connect to at the start of the test.

    Can be either a sequence of nodes to connect to for this chain.
    Or an empty sequence to connect to no nodes for this chain.
    Or the DEFAULT string literal meaning to connect to the built-in default nodes.
    """
    return 'DEFAULT'


@pytest.fixture(name='solana_inquirer')
def fixture_solana_inquirer(greenlet_manager, database, solana_nodes_connect_at_start):
    solana_inquirer = SolanaInquirer(
        greenlet_manager=greenlet_manager,
        database=database,
        helius=Helius(database=database),
    )
    with ExitStack() as stack:
        patch_solana_inquirer_nodes(
            stack=stack,
            solana_inquirer=solana_inquirer,
            solana_nodes_connect_at_start=solana_nodes_connect_at_start,
        )
        yield solana_inquirer


@pytest.fixture(name='solana_manager')
def fixture_solana_manager(solana_inquirer):
    return SolanaManager(node_inquirer=solana_inquirer)


@pytest.fixture(name='blockchain')
def fixture_blockchain(
        ethereum_manager,
        optimism_manager,
        polygon_pos_manager,
        arbitrum_one_manager,
        base_manager,
        gnosis_manager,
        scroll_manager,
        binance_sc_manager,
        kusama_manager,
        polkadot_manager,
        avalanche_manager,
        zksync_lite_manager,
        bitcoin_manager,
        bitcoin_cash_manager,
        solana_manager,
        blockchain_accounts,
        inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
        greenlet_manager,
        ethereum_modules,
        start_with_valid_premium,
        rotki_premium_credentials,
        database,
        data_dir,
        beaconchain,
        btc_derivation_gap_limit,
        username,
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(
            credentials=rotki_premium_credentials,
            username=username,
            msg_aggregator=messages_aggregator,
            db=database,
        )

    return ChainsAggregator(
        blockchain_accounts=blockchain_accounts,
        ethereum_manager=ethereum_manager,
        optimism_manager=optimism_manager,
        polygon_pos_manager=polygon_pos_manager,
        arbitrum_one_manager=arbitrum_one_manager,
        base_manager=base_manager,
        gnosis_manager=gnosis_manager,
        scroll_manager=scroll_manager,
        binance_sc_manager=binance_sc_manager,
        kusama_manager=kusama_manager,
        polkadot_manager=polkadot_manager,
        avalanche_manager=avalanche_manager,
        zksync_lite_manager=zksync_lite_manager,
        bitcoin_manager=bitcoin_manager,
        bitcoin_cash_manager=bitcoin_cash_manager,
        solana_manager=solana_manager,
        msg_aggregator=messages_aggregator,
        database=database,
        greenlet_manager=greenlet_manager,
        premium=premium,
        eth_modules=ethereum_modules,
        data_directory=data_dir,
        beaconchain=beaconchain,
        btc_derivation_gap_limit=btc_derivation_gap_limit,
    )
