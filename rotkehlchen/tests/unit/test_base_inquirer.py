from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.base import BASE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer


@pytest.mark.vcr
@pytest.mark.parametrize(*BASE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('base_accounts', [['0xCace5b3c29211740E595850E80478416eE77cA21']])  # to connect to nodes  # noqa: E501
def test_base_nodes_prune_and_archive_status(
        base_manager_connect_at_start: list[tuple],
        base_inquirer: 'BaseInquirer',
):
    """Checks that connecting to a set of base nodes, the capabilities of those nodes are known and
    stored. It tests the nodes one by one to avoid the randomness of the connections to the nodes
    while running with the VCR cassettes.
    """
    base_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
    wait_until_all_nodes_connected(
        connect_at_start=base_manager_connect_at_start,
        evm_inquirer=base_inquirer,
    )
    for node_name, web3_node in base_inquirer.rpc_mapping.items():
        if node_name.endpoint == 'https://base.blockpi.network/v1/rpc/public':
            assert not web3_node.is_pruned
            # not checking for archive here, as some times it is and some not
        elif node_name.endpoint in {'https://mainnet.base.org', 'https://rpc.ankr.com/base'}:
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name.endpoint == 'https://base.publicnode.com':
            assert web3_node.is_pruned
            assert not web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(base_inquirer.rpc_mapping) == len(base_manager_connect_at_start)
