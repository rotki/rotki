import json
import os
from typing import List

import pytest
from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.blockchain import Blockchain
from rotkehlchen.crypto import address_encoder, privatekey_to_address, sha3
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.ethchain import Ethchain
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.tests.utils.blockchain import geth_create_blockchain
from rotkehlchen.tests.utils.tests import cleanup_tasks
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress


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
def etherscan(database, messages_aggregator):
    return Etherscan(database=database, msg_aggregator=messages_aggregator)


@pytest.fixture
def ethchain_client(ethrpc_port, etherscan):
    ethrpc_endpoint = f'http://localhost:{ethrpc_port}'
    return Ethchain(ethrpc_endpoint, etherscan=etherscan, attempt_connect=False)


def _geth_blockchain(
        request,
        ethchain_client,
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
        ethchain_client=ethchain_client,
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
        ethchain_client,
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
        ethchain_client=ethchain_client,
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
def blockchain(
        blockchain_backend,  # pylint: disable=unused-argument
        ethchain_client,
        blockchain_accounts,
        inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
        owned_eth_tokens,
):
    return Blockchain(
        blockchain_accounts=blockchain_accounts,
        owned_eth_tokens=owned_eth_tokens,
        ethchain=ethchain_client,
        msg_aggregator=messages_aggregator,
    )
