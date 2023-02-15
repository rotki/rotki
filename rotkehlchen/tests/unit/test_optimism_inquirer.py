import pytest

from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.optimism import OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED


@pytest.mark.parametrize(*OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
def test_optimism_nodes_prune_and_archive_status(
        optimism_manager_connect_at_start,
        optimism_inquirer,
):
    """Checks that connecting to a set of optimism nodes, the capabilities of those nodes are known and stored."""  # noqa: E501
    wait_until_all_nodes_connected(
        connect_at_start=optimism_manager_connect_at_start,
        evm_inquirer=optimism_inquirer,
    )
    for node_name, web3_node in optimism_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://rpc.ankr.com/optimism':
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name.endpoint == 'https://opt-mainnet.nodereal.io/v1/e85935b614124789b99aa92930aca9a4':  # noqa: E501
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name.endpoint == 'https://mainnet.optimism.io':
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name.endpoint == 'https://optimism-mainnet.public.blastapi.io':
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')
