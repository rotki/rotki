from typing import List, Optional, Sequence

import pytest

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.chain.substrate.manager import SubstrateChainProperties, SubstrateManager
from rotkehlchen.chain.substrate.typing import KusamaAddress, SubstrateChain
from rotkehlchen.db.settings import DEFAULT_BTC_DERIVATION_GAP_LIMIT
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.substrate import (
    KUSAMA_DEFAULT_OWN_RPC_ENDPOINT,
    KUSAMA_SS58_FORMAT,
    KUSAMA_TOKEN,
    KUSAMA_TOKEN_DECIMALS,
    wait_until_all_substrate_nodes_connected,
)
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress, EthTokenInfo


@pytest.fixture(name='number_of_eth_accounts')
def fixture_number_of_eth_accounts():
    return 4


@pytest.fixture(name='ethereum_accounts')
def fixture_ethereum_accounts(number_of_eth_accounts) -> List[ChecksumEthAddress]:
    return [make_ethereum_address() for x in range(number_of_eth_accounts)]


@pytest.fixture(name='btc_accounts')
def fixture_btc_accounts() -> List[BTCAddress]:
    return []


@pytest.fixture(name='ksm_accounts')
def fixture_ksm_accounts() -> List[KusamaAddress]:
    """As per feature requirements, instantiating SubstrateManager won't trigger
    the logic that attempts to connect to the nodes. Use this fixture with KSM
    addresses on tests (e.g. integration/API tests) that require connection
    since instantiation.
    """
    return []


@pytest.fixture(name='blockchain_accounts')
def fixture_blockchain_accounts(
        ethereum_accounts: List[ChecksumEthAddress],
        btc_accounts: List[BTCAddress],
        ksm_accounts: List[KusamaAddress],
) -> BlockchainAccounts:
    return BlockchainAccounts(
        eth=ethereum_accounts,
        btc=btc_accounts.copy(),
        ksm=ksm_accounts.copy(),
    )


@pytest.fixture(name='ethrpc_endpoint')
def fixture_ethrpc_endpoint() -> Optional[str]:
    return None


@pytest.fixture(name='ethereum_manager_connect_at_start')
def fixture_ethereum_manager_connect_at_start() -> Sequence[NodeName]:
    return ()


@pytest.fixture
def all_eth_tokens() -> List[EthTokenInfo]:
    return AssetResolver().get_all_eth_token_info()


@pytest.fixture(name='etherscan')
def fixture_etherscan(database, messages_aggregator):
    return Etherscan(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture(name='ethereum_manager')
def fixture_ethereum_manager(
        etherscan,
        messages_aggregator,
        ethrpc_endpoint,
        ethereum_manager_connect_at_start,
        greenlet_manager,
        database,
):
    if ethrpc_endpoint is None:
        endpoint = 'http://localhost:8545'
    else:
        endpoint = ethrpc_endpoint

    manager = EthereumManager(
        ethrpc_endpoint=endpoint,
        etherscan=etherscan,
        database=database,
        msg_aggregator=messages_aggregator,
        greenlet_manager=greenlet_manager,
        connect_at_start=ethereum_manager_connect_at_start,
    )
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=manager,
    )

    return manager


@pytest.fixture(name='ksm_rpc_endpoint')
def fixture_ksm_rpc_endpoint() -> Optional[str]:
    return None


@pytest.fixture(name='kusama_manager_connect_at_start')
def fixture_kusama_manager_connect_at_start() -> Sequence[NodeName]:
    return ()


@pytest.fixture(name='kusama_available_node_attributes_map')
def fixture_kusama_available_node_attributes_map():
    return {}


@pytest.fixture(name='kusama_manager')
def fixture_kusama_manager(
        messages_aggregator,
        greenlet_manager,
        ksm_accounts,
        ksm_rpc_endpoint,
        kusama_available_node_attributes_map,
        kusama_manager_connect_at_start,
):
    own_rpc_endpoint = (
        ksm_rpc_endpoint if ksm_rpc_endpoint is not None else KUSAMA_DEFAULT_OWN_RPC_ENDPOINT
    )
    kusama_manager = SubstrateManager(
        chain=SubstrateChain.KUSAMA,
        msg_aggregator=messages_aggregator,
        greenlet_manager=greenlet_manager,
        connect_at_start=kusama_manager_connect_at_start,
        connect_on_startup=bool(ksm_accounts),
        own_rpc_endpoint=own_rpc_endpoint,
    )
    if len(kusama_available_node_attributes_map) != 0:
        # When connection is persisted <SubstrateManager.chain_properties> must
        # be set manually (either requesting the chain or hard coded)
        kusama_manager.available_node_attributes_map = kusama_available_node_attributes_map
        kusama_manager._set_available_nodes_call_order()
        # NB: for speeding up tests, instead of requesting the properties of
        # the chain, we manually set them.
        kusama_manager.chain_properties = SubstrateChainProperties(
            ss58_format=KUSAMA_SS58_FORMAT,
            token=KUSAMA_TOKEN,
            token_decimals=KUSAMA_TOKEN_DECIMALS,
        )
    else:
        wait_until_all_substrate_nodes_connected(
            substrate_manager_connect_at_start=kusama_manager_connect_at_start,
            substrate_manager=kusama_manager,
        )

    return kusama_manager


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
