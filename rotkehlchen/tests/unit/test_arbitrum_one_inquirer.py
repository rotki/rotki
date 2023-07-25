import pytest

from rotkehlchen.tests.utils.arbitrum_one import (
    ARBITRUM_ONE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
)
from rotkehlchen.tests.utils.factories import make_evm_address


@pytest.mark.parametrize(*ARBITRUM_ONE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('arbitrum_one_accounts', [[make_evm_address()]])  # to connect to nodes
def test_arbitrum_one_nodes_prune_and_archive_status(
        arbitrum_one_manager_connect_at_start,
        arbitrum_one_inquirer,
):
    """Checks that connecting to a set of Arbitrum One nodes, the capabilities of those nodes
    are known and stored.

    This test is sort of fast and is not VCRed due to the randomness of the connection
    to the nodes not being able to be replicated in a reproducible way in the cassetes.
    """
    for node_name, web3_node in arbitrum_one_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://arbitrum-one-archive.allthatnode.com':
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name.endpoint == 'https://arbitrum.blockpi.network/v1/rpc/public':
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        # TODO add a check for a pruned node.
        # TODO All these calls should be mocked. Can't rely on a remote always being pruned, full or archive for a CI test  # noqa: E501
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(arbitrum_one_inquirer.web3_mapping) == len(arbitrum_one_manager_connect_at_start)


def test_block_by_time_close_to_genesis(arbitrum_one_inquirer):
    """Checks that etherscan handles block number by time query correctly for a timestamp
    very close to genesis"""
    result = arbitrum_one_inquirer.get_blocknumber_by_time(1622243344)
    assert result == 1
