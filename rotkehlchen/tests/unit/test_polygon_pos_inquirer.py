import pytest

from rotkehlchen.tests.utils.polygon_pos import (
    ALCHEMY_RPC_ENDPOINT,
    POLYGON_POS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
)


@pytest.mark.vcr
@pytest.mark.parametrize(*POLYGON_POS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('polygon_pos_accounts', [['0xCace5b3c29211740E595850E80478416eE77cA21']])  # to connect to nodes  # noqa: E501
def test_polygon_pos_nodes_prune_and_archive_status(
        polygon_pos_manager_connect_at_start,
        polygon_pos_inquirer,
):
    """Checks that connecting to a set of polygon POS nodes, the capabilities of those nodes are
    known and stored. It tests the nodes one by one to avoid the randomness of the connections to
    the nodes while running with the VCR cassettes."""
    for node_name, web3_node in polygon_pos_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://polygon-bor.publicnode.com':
            assert web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name.endpoint in ('https://rpc.ankr.com/polygon', ALCHEMY_RPC_ENDPOINT):
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(polygon_pos_inquirer.web3_mapping) == len(polygon_pos_manager_connect_at_start)
