import json
import os
from typing import List, Optional, Sequence

import pytest
from eth_utils.address import to_checksum_address

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.crypto import address_encoder, privatekey_to_address, sha3
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.blockchain import geth_create_blockchain
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.tests import cleanup_tasks
from rotkehlchen.tests.utils.zerion import create_zerion_patch, wait_until_zerion_is_initialized
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress, EthTokenInfo


@pytest.fixture
def number_of_eth_accounts():
    return 4


@pytest.fixture
def privatekey_seed(request):
    """ Private key template, allow different keys to be used for each test to
    avoid collisions.
    """
    return request.node.name + ':{}'


@pytest.fixture
def private_keys(number_of_eth_accounts, privatekey_seed):
    """ Private keys for each raiden node. """

    # Note: The fixtures depend on the order of the private keys
    result = [
        sha3(privatekey_seed.format(position).encode())
        for position in range(number_of_eth_accounts)
    ]

    # this must not happen, otherwise the keys and addresses will be equal!
    assert len(set(result)) == number_of_eth_accounts, '`privatekey_seed` generated repeated keys'

    return result


@pytest.fixture
def ethereum_accounts(private_keys) -> List[ChecksumEthAddress]:
    return [
        to_checksum_address(address_encoder(privatekey_to_address(key)))
        for key in sorted(set(private_keys))
    ]


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
def ethrpc_port(port_generator):
    port = next(port_generator)
    return port


@pytest.fixture
def ethrpc_endpoint() -> Optional[str]:
    return None


@pytest.fixture
def ethereum_manager_connect_at_start() -> Sequence[NodeName]:
    return ()


@pytest.fixture
def eth_p2p_port(port_generator):
    port = next(port_generator)
    return port


@pytest.fixture
def all_eth_tokens() -> List[EthTokenInfo]:
    return AssetResolver().get_all_eth_token_info()


@pytest.fixture
def etherscan(database, messages_aggregator):
    return Etherscan(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture
def ethereum_manager(
        ethrpc_port,
        etherscan,
        messages_aggregator,
        ethrpc_endpoint,
        ethereum_manager_connect_at_start,
        greenlet_manager,
        database,
):
    if ethrpc_endpoint is None:
        endpoint = f'http://localhost:{ethrpc_port}'
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


def _geth_blockchain(
        request,
        ethereum_manager,
        private_keys,
        eth_p2p_port,
        ethrpc_endpoint,
        ethrpc_port,
        tmpdir,
        random_marker,
        genesis_path,
):
    """ Helper to do proper cleanup. """
    geth_process = geth_create_blockchain(
        ethereum_manager=ethereum_manager,
        private_keys=private_keys,
        gethport=eth_p2p_port,
        gethrpcendpoint=ethrpc_endpoint,
        gethrpcport=ethrpc_port,
        base_datadir=str(tmpdir),
        verbosity=request.config.option.verbose,
        random_marker=random_marker,
        genesis_path=genesis_path,
    )

    def _cleanup():
        geth_process.terminate()

        cleanup_tasks()

    request.addfinalizer(_cleanup)
    return geth_process


@pytest.fixture
def cached_genesis():
    return False


@pytest.fixture
def have_blockchain_backend():
    return False


@pytest.fixture
def blockchain_backend(
        request,
        ethereum_manager,
        private_keys,
        ethrpc_port,
        eth_p2p_port,
        tmpdir,
        random_marker,
        cached_genesis,
        have_blockchain_backend,
):
    ethrpc_endpoint = f'http://localhost:{ethrpc_port}'
    if not have_blockchain_backend:
        return None

    genesis_path = None
    if cached_genesis:
        genesis_path = os.path.join(str(tmpdir), 'generated_genesis.json')

        with open(genesis_path, 'w') as handler:
            json.dump(cached_genesis, handler)

    return _geth_blockchain(
        request=request,
        ethereum_manager=ethereum_manager,
        private_keys=private_keys,
        eth_p2p_port=eth_p2p_port,
        ethrpc_endpoint=ethrpc_endpoint,
        ethrpc_port=ethrpc_port,
        tmpdir=tmpdir,
        random_marker=random_marker,
        genesis_path=genesis_path,
    )


@pytest.fixture
def ethereum_modules() -> List[str]:
    return []


@pytest.fixture
def blockchain(
        blockchain_backend,  # pylint: disable=unused-argument
        ethereum_manager,
        blockchain_accounts,
        inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
        greenlet_manager,
        ethereum_modules,
        start_with_valid_premium,
        rotki_premium_credentials,
        database,
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    with create_zerion_patch():
        chain_manager = ChainManager(
            blockchain_accounts=blockchain_accounts,
            ethereum_manager=ethereum_manager,
            msg_aggregator=messages_aggregator,
            database=database,
            greenlet_manager=greenlet_manager,
            premium=premium,
            eth_modules=ethereum_modules,
        )
        wait_until_zerion_is_initialized(chain_manager)

    return chain_manager
