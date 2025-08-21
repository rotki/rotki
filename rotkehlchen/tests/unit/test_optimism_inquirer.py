from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.optimism import OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


@pytest.mark.vcr
@pytest.mark.parametrize(*OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('optimism_accounts', [['0xCace5b3c29211740E595850E80478416eE77cA21']])  # to connect to nodes  # noqa: E501
def test_optimism_nodes_prune_and_archive_status(
        optimism_manager_connect_at_start: list[tuple],
        optimism_inquirer: 'OptimismInquirer',
):
    """Checks that connecting to a set of optimism nodes, the capabilities of those nodes are known
    and stored. It tests the nodes one by one to avoid the randomness of the connections to the
    nodes while running with the VCR cassettes."""
    optimism_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
    wait_until_all_nodes_connected(
        connect_at_start=optimism_manager_connect_at_start,
        evm_inquirer=optimism_inquirer,
    )
    for node_name, web3_node in optimism_inquirer.rpc_mapping.items():
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

    assert len(optimism_inquirer.rpc_mapping) == len(optimism_manager_connect_at_start)
