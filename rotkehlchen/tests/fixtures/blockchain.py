from typing import List, Optional, Sequence

import pytest

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress, EthTokenInfo


@pytest.fixture
def number_of_eth_accounts():
    return 4


@pytest.fixture
def ethereum_accounts(number_of_eth_accounts) -> List[ChecksumEthAddress]:
    return [make_ethereum_address() for x in range(number_of_eth_accounts)]


@pytest.fixture
def btc_accounts() -> List[BTCAddress]:
    return []


@pytest.fixture
def blockchain_accounts(
        ethereum_accounts: List[ChecksumEthAddress],
        btc_accounts: List[BTCAddress],
) -> BlockchainAccounts:
    return BlockchainAccounts(eth=ethereum_accounts, btc=btc_accounts.copy())


@pytest.fixture
def ethrpc_endpoint() -> Optional[str]:
    return None


@pytest.fixture
def ethereum_manager_connect_at_start() -> Sequence[NodeName]:
    return ()


@pytest.fixture
def all_eth_tokens() -> List[EthTokenInfo]:
    return AssetResolver().get_all_eth_token_info()


@pytest.fixture
def etherscan(database, messages_aggregator):
    return Etherscan(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture
def ethereum_manager(
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


@pytest.fixture
def ethereum_modules() -> List[str]:
    return []


@pytest.fixture
def beaconchain(database, messages_aggregator):
    return BeaconChain(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture
def blockchain(
        ethereum_manager,
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
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    chain_manager = ChainManager(
        blockchain_accounts=blockchain_accounts,
        ethereum_manager=ethereum_manager,
        msg_aggregator=messages_aggregator,
        database=database,
        greenlet_manager=greenlet_manager,
        premium=premium,
        eth_modules=ethereum_modules,
        data_directory=data_dir,
        beaconchain=beaconchain,
    )

    return chain_manager
