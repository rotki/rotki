from typing import List, Optional, Sequence

import pytest

from rotkehlchen.chain.avalanche.manager import AvalancheManager
from rotkehlchen.chain.ethereum.decoding import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName
from rotkehlchen.chain.ethereum.transactions import EthTransactions
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.chain.substrate.manager import SubstrateChainProperties, SubstrateManager
from rotkehlchen.chain.substrate.types import KusamaAddress, PolkadotAddress, SubstrateChain
from rotkehlchen.constants.assets import A_DOT
from rotkehlchen.db.settings import DEFAULT_BTC_DERIVATION_GAP_LIMIT
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.covalent import Covalent
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_DEFAULT_OWN_RPC_ENDPOINT,
    KUSAMA_SS58_FORMAT,
    KUSAMA_TOKEN,
    KUSAMA_TOKEN_DECIMALS,
    POLKADOT_SS58_FORMAT,
    wait_until_all_substrate_nodes_connected,
)
from rotkehlchen.types import BTCAddress, ChecksumEvmAddress


@pytest.fixture(name='number_of_eth_accounts')
def fixture_number_of_eth_accounts():
    return 4


@pytest.fixture(name='ethereum_accounts')
def fixture_ethereum_accounts(number_of_eth_accounts) -> List[ChecksumEvmAddress]:
    return [make_ethereum_address() for x in range(number_of_eth_accounts)]


@pytest.fixture(name='btc_accounts')
def fixture_btc_accounts() -> List[BTCAddress]:
    return []


@pytest.fixture(name='bch_accounts')
def fixture_bch_accounts() -> List[BTCAddress]:
    return []


@pytest.fixture(name='ksm_accounts')
def fixture_ksm_accounts() -> List[KusamaAddress]:
    """As per feature requirements, instantiating SubstrateManager won't trigger
    the logic that attempts to connect to the nodes. Use this fixture with KSM
    addresses on tests (e.g. integration/API tests) that require connection
    since instantiation.
    """
    return []


@pytest.fixture(name='dot_accounts')
def fixture_dot_accounts() -> List[PolkadotAddress]:
    """As per feature requirements, instantiating SubstrateManager won't trigger
    the logic that attempts to connect to the nodes. Use this fixture with KSM
    addresses on tests (e.g. integration/API tests) that require connection
    since instantiation.
    """
    return []


@pytest.fixture(name='avax_accounts')
def fixture_avax_accounts() -> List[ChecksumEvmAddress]:
    return []


@pytest.fixture(name='blockchain_accounts')
def fixture_blockchain_accounts(
        ethereum_accounts: List[ChecksumEvmAddress],
        btc_accounts: List[BTCAddress],
        bch_accounts: List[BTCAddress],
        ksm_accounts: List[KusamaAddress],
        dot_accounts: List[PolkadotAddress],
        avax_accounts: List[ChecksumEvmAddress],
) -> BlockchainAccounts:
    return BlockchainAccounts(
        eth=ethereum_accounts,
        btc=btc_accounts.copy(),
        bch=bch_accounts.copy(),
        ksm=ksm_accounts.copy(),
        dot=dot_accounts.copy(),
        avax=avax_accounts.copy(),
    )


@pytest.fixture(name='ethrpc_endpoint')
def fixture_ethrpc_endpoint() -> Optional[str]:
    return None


@pytest.fixture(name='ethereum_manager_connect_at_start')
def fixture_ethereum_manager_connect_at_start() -> Sequence[NodeName]:
    return ()


@pytest.fixture(name='etherscan')
def fixture_etherscan(database, messages_aggregator):
    return Etherscan(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture(name='covalent_avalanche')
def fixture_covalent_avalanche(messages_aggregator, database):
    return Covalent(database=database, msg_aggregator=messages_aggregator, chain_id='43114')


@pytest.fixture(name='ethereum_manager')
def fixture_ethereum_manager(
        etherscan,
        messages_aggregator,
        ethereum_manager_connect_at_start,
        greenlet_manager,
        database,
):
    manager = EthereumManager(
        etherscan=etherscan,
        msg_aggregator=messages_aggregator,
        greenlet_manager=greenlet_manager,
        connect_at_start=ethereum_manager_connect_at_start,
        database=database,
    )
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=manager,
    )

    return manager


@pytest.fixture(name='evm_transaction_decoder')
def fixture_evm_transaction_decoder(
        database,
        ethereum_manager,
        eth_transactions,
        function_scope_messages_aggregator,
):
    return EVMTransactionDecoder(
        database=database,
        ethereum_manager=ethereum_manager,
        eth_transactions=eth_transactions,
        msg_aggregator=function_scope_messages_aggregator,
    )


@pytest.fixture(name='eth_transactions')
def fixture_eth_transactions(
        database,
        ethereum_manager,
):  # noqa: E501
    return EthTransactions(
        ethereum=ethereum_manager,
        database=database,
    )


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
        chain=SubstrateChain.KUSAMA,
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
        if chain_type == SubstrateChain.KUSAMA:
            substrate_manager.chain_properties = SubstrateChainProperties(
                ss58_format=KUSAMA_SS58_FORMAT,
                token=KUSAMA_TOKEN,
                token_decimals=KUSAMA_TOKEN_DECIMALS,
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
        chain_type=SubstrateChain.KUSAMA,
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
        chain_type=SubstrateChain.POLKADOT,
        rpc_endpoint=dot_rpc_endpoint,
        available_node_attributes_map=polkadot_available_node_attributes_map,
        connect_at_start=polkadot_manager_connect_at_start,
    )


@pytest.fixture(name='avalanche_manager')
def fixture_avalanche_manager(
    messages_aggregator,
    covalent_avalanche,
):
    avalanche_manager = AvalancheManager(
        avaxrpc_endpoint="https://api.avax.network/ext/bc/C/rpc",
        covalent=covalent_avalanche,
        msg_aggregator=messages_aggregator,
    )
    return avalanche_manager


@pytest.fixture(name='ethereum_modules')
def fixture_ethereum_modules() -> List[str]:
    return []


@pytest.fixture(name='beaconchain')
def fixture_beaconchain(database, messages_aggregator):
    return BeaconChain(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture(name='btc_derivation_gap_limit')
def fixture_btc_derivation_gap_limit():
    return DEFAULT_BTC_DERIVATION_GAP_LIMIT


@pytest.fixture
def blockchain(
        ethereum_manager,
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

    chain_manager = ChainManager(
        blockchain_accounts=blockchain_accounts,
        ethereum_manager=ethereum_manager,
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

    return chain_manager
