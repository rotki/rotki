import pytest

from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.scroll import (
    ANKR_SCROLL_NODE,
    BLOCKPI_SCROLL_NODE,
    ONE_RPC_SCROLL_NODE,
    SCROLL_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
)


@pytest.mark.parametrize(*SCROLL_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('scroll_accounts', [[make_evm_address()]])  # to connect to nodes
def test_scroll_nodes_prune_and_archive_status(
        scroll_manager_connect_at_start,
        scroll_inquirer,
):
    """Checks that connecting to a set of scroll nodes, the capabilities of those nodes are
    known and stored. This test is sort of fast and is not VCRed due to the randomness of the
    connection to the nodes not being able to be replicated in a reproducible way in the cassetes.
    """
    for node_name, web3_node in scroll_inquirer.web3_mapping.items():
        if node_name in {BLOCKPI_SCROLL_NODE, ANKR_SCROLL_NODE, ONE_RPC_SCROLL_NODE}:
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(scroll_inquirer.web3_mapping) == len(scroll_manager_connect_at_start)
