from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.gnosis import GNOSIS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer


@pytest.mark.vcr
@pytest.mark.parametrize(*GNOSIS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('gnosis_accounts', [['0xCace5b3c29211740E595850E80478416eE77cA21']])  # to connect to nodes  # noqa: E501
def test_gnosis_nodes_prune_and_archive_status(
        gnosis_manager_connect_at_start: list[tuple],
        gnosis_inquirer: 'GnosisInquirer',
):
    """Checks that connecting to a set of gnosis nodes, the capabilities of those nodes are
    known and stored. It tests the nodes one by one to avoid the randomness of the connections to
    the nodes while running with the VCR cassettes.
    """
    gnosis_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
    wait_until_all_nodes_connected(
        connect_at_start=gnosis_manager_connect_at_start,
        evm_inquirer=gnosis_inquirer,
    )
    for node_name, web3_node in gnosis_inquirer.rpc_mapping.items():
        if node_name.endpoint == 'https://gnosis.blockpi.network/v1/rpc/public':
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name.endpoint == 'https://rpc.ankr.com/gnosis':
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name.endpoint in {'https://1rpc.io/gnosis', 'https://gnosis.publicnode.com'}:
            assert web3_node.is_pruned
            assert not web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(gnosis_inquirer.rpc_mapping) == len(gnosis_manager_connect_at_start)
