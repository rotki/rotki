import pytest

from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.polygon_pos import (
    POLYGON_POS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
)


@pytest.mark.parametrize(*POLYGON_POS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('polygon_pos_accounts', [[make_evm_address()]])  # to connect to nodes
def test_polygon_pos_nodes_prune_and_archive_status(
        polygon_pos_manager_connect_at_start,
        polygon_pos_inquirer,
):
    """Checks that connecting to a set of polygon POS nodes, the capabilities of those nodes are known and stored.

    This test is sort of fast and is not VCRed due to the randomness of the connection
    to the nodes not being able to be replicated in a reproducible way in the cassetes.
    """  # noqa: E501
    for node_name, web3_node in polygon_pos_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://polygon-bor.publicnode.com':
            assert web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name.endpoint in ('https://rpc.ankr.com/polygon', 'https://polygon-mainnet.g.alchemy.com/v2/uNdnI7_6XXc7ayswOxtd_RuTBGojJhIf'):
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(polygon_pos_inquirer.web3_mapping) == len(polygon_pos_manager_connect_at_start)
