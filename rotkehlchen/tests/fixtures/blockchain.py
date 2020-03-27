import json
import os
from typing import List

import pytest
from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.makerdao import MakerDAO
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.crypto import address_encoder, privatekey_to_address, sha3
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.externalapis.alethio import Alethio
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.tests.utils.blockchain import geth_create_blockchain
from rotkehlchen.tests.utils.tests import cleanup_tasks
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
def eth_p2p_port(port_generator):
    port = next(port_generator)
    return port


@pytest.fixture
def all_eth_tokens() -> List[EthTokenInfo]:
    return AssetResolver().get_all_eth_tokens()


@pytest.fixture
def etherscan(database, messages_aggregator):
    return Etherscan(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture
def alethio(database, messages_aggregator, all_eth_tokens):
    return Alethio(
        database=database,
        msg_aggregator=messages_aggregator,
        all_eth_tokens=all_eth_tokens,
    )


@pytest.fixture
def ethereum_manager(ethrpc_port, etherscan, messages_aggregator):
    ethrpc_endpoint = f'http://localhost:{ethrpc_port}'
    return EthereumManager(
        ethrpc_endpoint=ethrpc_endpoint,
        etherscan=etherscan,
        msg_aggregator=messages_aggregator,
        attempt_connect=False,
    )


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
def owned_eth_tokens() -> List[EthereumToken]:
    return []


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
        owned_eth_tokens,
        ethereum_modules,
        alethio,
        database,
):
    modules = {}
    for given_module in ethereum_modules:
        if given_module == 'makerdao':
            modules['makerdao'] = MakerDAO(
                ethereum_manager=ethereum_manager,
                database=database,
                msg_aggregator=messages_aggregator,
            )
        else:
            raise AssertionError(f'Unrecognized ethereum module {given_module} in test setup')

    return ChainManager(
        blockchain_accounts=blockchain_accounts,
        owned_eth_tokens=owned_eth_tokens,
        ethereum_manager=ethereum_manager,
        msg_aggregator=messages_aggregator,
        alethio=alethio,
        greenlet_manager=greenlet_manager,
        eth_modules=modules,
    )
