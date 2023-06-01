from collections.abc import Sequence
from contextlib import ExitStack
from typing import Literal, Optional, Union
from unittest.mock import patch

import pytest

from rotkehlchen.chain.accounts import BlockchainAccounts
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.avalanche.manager import AvalancheManager
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.types import NodeName
from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
from rotkehlchen.chain.optimism.manager import OptimismManager
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.chain.optimism.transactions import OptimismTransactions
from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
from rotkehlchen.chain.substrate.manager import SubstrateChainProperties, SubstrateManager
from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.constants.assets import A_DOT, A_KSM
from rotkehlchen.db.settings import DEFAULT_BTC_DERIVATION_GAP_LIMIT
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.covalent import Covalent
from rotkehlchen.externalapis.opensea import Opensea
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.evm import maybe_mock_evm_inquirer
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import mock_proxies, patch_avalanche_request
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_DEFAULT_OWN_RPC_ENDPOINT,
    KUSAMA_MAIN_ASSET_DECIMALS,
    KUSAMA_SS58_FORMAT,
    POLKADOT_SS58_FORMAT,
    wait_until_all_substrate_nodes_connected,
)
from rotkehlchen.types import BTCAddress, ChainID, ChecksumEvmAddress, SupportedBlockchain


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

    if isinstance(manager_connect_at_start, str):
        assert manager_connect_at_start == 'DEFAULT'
        nodes_to_connect_to = database.get_rpc_nodes(blockchain, only_active=True)
    else:
        nodes_to_connect_to = manager_connect_at_start
        with database.user_write() as write_cursor:
            write_cursor.execute(  # Delete all but etherscan endpoint
                'DELETE FROM rpc_nodes WHERE blockchain=? and endpoint!=""',
                (blockchain.value,))
        for entry in nodes_to_connect_to:
            if entry.node_info.endpoint != '':  # don't re-add etherscan
                database.add_rpc_node(entry)

    with ExitStack() as init_stack:
        if mock_other_web3 is True:
            init_stack.enter_context(patch(  # at init of Inquirer attempt no connection if mocking
                class_path,
                return_value=lambda *args: None,
            ))
        inquirer = klass(
            greenlet_manager=greenlet_manager,
            database=database,
        )

    if mock_other_web3 is False:  # no mocking means we should wait till connect is done
        wait_until_all_nodes_connected(
            connect_at_start=nodes_to_connect_to,
            evm_inquirer=inquirer,
        )

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


@pytest.fixture(name='btc_accounts')
def fixture_btc_accounts() -> list[BTCAddress]:
    return []


@pytest.fixture(name='bch_accounts')
def fixture_bch_accounts() -> list[BTCAddress]:
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
        avax_accounts: list[ChecksumEvmAddress],
        btc_accounts: list[BTCAddress],
        bch_accounts: list[BTCAddress],
        ksm_accounts: list[SubstrateAddress],
        dot_accounts: list[SubstrateAddress],
) -> BlockchainAccounts:
    return BlockchainAccounts(
        eth=tuple(ethereum_accounts),
        optimism=tuple(optimism_accounts),
        polygon_pos=tuple(polygon_pos_accounts),
        avax=tuple(avax_accounts),
        btc=tuple(btc_accounts),
        bch=tuple(bch_accounts),
        ksm=tuple(ksm_accounts),
        dot=tuple(dot_accounts),
    )


@pytest.fixture(name='ethrpc_endpoint')
def fixture_ethrpc_endpoint() -> Optional[str]:
    return None


@pytest.fixture(name='covalent_avalanche')
def fixture_covalent_avalanche(messages_aggregator, database):
    return Covalent(database=database, msg_aggregator=messages_aggregator, chain_id='43114')


@pytest.fixture(name='ethereum_manager_connect_at_start')
def fixture_ethereum_manager_connect_at_start() -> Union[Literal['DEFAULT'], Sequence[NodeName]]:
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


@pytest.fixture(name='avalanche_mock_data')
def fixture_avalance_mock_data():
    """Can contain mocked data for both etherscan and web3 requests"""
    return {}


@pytest.fixture(name='mock_other_web3')
def fixture_mock_other_web3(network_mocking, should_mock_web3):
    """Just like fixture_web3_mocking this decides but in boolean
    without yielding if web3 and related stuff should be mocked"""
    if network_mocking is False:
        return False
    if should_mock_web3:
        return True
    return False


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
):
    with patch_decoder_reload_data():
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
def fixture_eth_transactions(
        database,
        ethereum_inquirer,
):
    return EthereumTransactions(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
    )


@pytest.fixture(name='optimism_manager_connect_at_start')
def fixture_optimism_manager_connect_at_start() -> Union[Literal['DEFAULT'], Sequence[NodeName]]:
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
def fixture_optimism_transactions(
        database,
        optimism_inquirer,
):
    return OptimismTransactions(
        optimism_inquirer=optimism_inquirer,
        database=database,
    )


@pytest.fixture(name='optimism_transaction_decoder')
def fixture_optimism_transaction_decoder(
        database,
        optimism_inquirer,
        optimism_transactions,
):
    with patch_decoder_reload_data():
        yield OptimismTransactionDecoder(
            database=database,
            optimism_inquirer=optimism_inquirer,
            transactions=optimism_transactions,
        )


@pytest.fixture(name='polygon_pos_manager_connect_at_start')
def fixture_polygon_pos_manager_connect_at_start() -> Union[Literal['DEFAULT'], Sequence[NodeName]]:  # noqa: E501
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


@pytest.fixture(name='ksm_rpc_endpoint')
def fixture_ksm_rpc_endpoint() -> Optional[str]:
    return None


@pytest.fixture(name='dot_rpc_endpoint')
def fixture_dot_rpc_endpoint() -> Optional[str]:
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
        chain=SupportedBlockchain.KUSAMA,
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
def fixture_avalanche_manager(
        messages_aggregator,
        covalent_avalanche,
        network_mocking,
        avalanche_mock_data,
):
    avalanche_manager = AvalancheManager(
        avaxrpc_endpoint='https://api.avax.network/ext/bc/C/rpc',
        covalent=covalent_avalanche,
        msg_aggregator=messages_aggregator,
    )
    with patch('rotkehlchen.externalapis.covalent.COVALENT_KEYS', ('',)):
        if network_mocking:
            with patch_avalanche_request(avalanche_manager, avalanche_mock_data):
                yield avalanche_manager
        else:
            yield avalanche_manager


@pytest.fixture(name='ethereum_modules')
def fixture_ethereum_modules() -> list[str]:
    return []


@pytest.fixture(name='beaconchain')
def fixture_beaconchain(database, messages_aggregator):
    return BeaconChain(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture(name='opensea')
def fixture_opensea(database, messages_aggregator):
    return Opensea(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture(name='btc_derivation_gap_limit')
def fixture_btc_derivation_gap_limit():
    return DEFAULT_BTC_DERIVATION_GAP_LIMIT


@pytest.fixture(name='blockchain')
def fixture_blockchain(
        ethereum_manager,
        optimism_manager,
        polygon_pos_manager,
        kusama_manager,
        polkadot_manager,
        avalanche_manager,
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
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    chains_aggregator = ChainsAggregator(
        blockchain_accounts=blockchain_accounts,
        ethereum_manager=ethereum_manager,
        optimism_manager=optimism_manager,
        polygon_pos_manager=polygon_pos_manager,
        kusama_manager=kusama_manager,
        polkadot_manager=polkadot_manager,
        avalanche_manager=avalanche_manager,
        msg_aggregator=messages_aggregator,
        database=database,
        greenlet_manager=greenlet_manager,
        premium=premium,
        eth_modules=ethereum_modules,
        data_directory=data_dir,
        beaconchain=beaconchain,
        btc_derivation_gap_limit=btc_derivation_gap_limit,
    )

    return chains_aggregator


@pytest.fixture(name='ethereum_contracts')
def fixture_ethereum_contracts():
    return EvmContracts[Literal[ChainID.ETHEREUM]](ChainID.ETHEREUM)
