from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.binance_sc import (
    ANKR_BINANCE_SC_NODE,
    BINANCE_SC_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
    BLASTAPI_BINANCE_SC_NODE,
    LLAMARPC_BINANCE_SC_NODE,
    ONE_RPC_BINANCE_SC_NODE,
)
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer


@pytest.mark.vcr
@pytest.mark.parametrize(*BINANCE_SC_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('binance_sc_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])  # to connect to nodes  # noqa: E501
def test_binance_sc_nodes_prune_and_archive_status(
        binance_sc_manager_connect_at_start: list[tuple],
        binance_sc_inquirer: 'BinanceSCInquirer',
):
    """Checks that connecting to a set of BinanceSC nodes, the capabilities of those nodes are
    known and stored. It tests the nodes one by one to avoid the randomness of the connections
    to the nodes while running with the VCR cassettes.
    """
    binance_sc_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
    wait_until_all_nodes_connected(
        connect_at_start=binance_sc_manager_connect_at_start,
        evm_inquirer=binance_sc_inquirer,
    )
    for node_name, web3_node in binance_sc_inquirer.rpc_mapping.items():
        if node_name == ONE_RPC_BINANCE_SC_NODE:
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name == BLASTAPI_BINANCE_SC_NODE:
            assert not web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name == LLAMARPC_BINANCE_SC_NODE:
            assert web3_node.is_pruned
            assert not web3_node.is_archive
        elif node_name == ANKR_BINANCE_SC_NODE:
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(binance_sc_inquirer.rpc_mapping) == len(binance_sc_manager_connect_at_start)
