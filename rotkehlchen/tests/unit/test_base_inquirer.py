import pytest

from rotkehlchen.tests.utils.base import BASE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED
from rotkehlchen.tests.utils.factories import make_evm_address


@pytest.mark.parametrize(*BASE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('base_accounts', [[make_evm_address()]])  # to connect to nodes
def test_base_nodes_prune_and_archive_status(
        base_manager_connect_at_start,
        base_inquirer,
):
    """Checks that connecting to a set of base nodes, the capabilities of those nodes are known and stored.
    This test is sort of fast and is not VCRed due to the randomness of the connection
    to the nodes not being able to be replicated in a reproducible way in the cassetes.
    """  # noqa: E501
    for node_name, web3_node in base_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://base.blockpi.network/v1/rpc/public':
            assert not web3_node.is_pruned
            # not checking for archive here, as some times it is and some not
        elif node_name.endpoint in {'https://mainnet.base.org', 'https://rpc.ankr.com/base'}:
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name.endpoint == 'https://base.publicnode.com':
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(base_inquirer.web3_mapping) == len(base_manager_connect_at_start)
