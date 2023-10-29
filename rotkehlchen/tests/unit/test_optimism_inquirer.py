import pytest

from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.optimism import OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED


@pytest.mark.parametrize(*OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('optimism_accounts', [[make_evm_address()]])  # to connect to nodes
def test_optimism_nodes_prune_and_archive_status(
        optimism_manager_connect_at_start,
        optimism_inquirer,
):
    """Checks that connecting to a set of optimism nodes, the capabilities of those nodes are known and stored.

    This test is sort of fast and is not VCRed due to the randomness of the connection
    to the nodes not being able to be replicated in a reproducible way in the cassetes.
    """  # noqa: E501
    for node_name, web3_node in optimism_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://opt-mainnet.nodereal.io/v1/e85935b614124789b99aa92930aca9a4':
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name.endpoint in {'https://mainnet.optimism.io', 'https://rpc.ankr.com/optimism'}:
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name.endpoint == 'https://optimism-mainnet.public.blastapi.io':
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(optimism_inquirer.web3_mapping) == len(optimism_manager_connect_at_start)
