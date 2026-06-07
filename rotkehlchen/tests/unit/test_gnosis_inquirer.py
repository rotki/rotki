from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.gnosis import GNOSIS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED
from rotkehlchen.types import SupportedBlockchain

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


# pin to a single live node so the request order is deterministic and VCR-able
GNOSIS_SINGLE_NODE: list[WeightedNode] = [WeightedNode(
    node_info=NodeName(
        name='gnosis official',
        endpoint='https://rpc.gnosischain.com',
        owned=False,
        blockchain=SupportedBlockchain.GNOSIS,
    ),
    active=True,
    weight=ONE,
)]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_manager_connect_at_start', [GNOSIS_SINGLE_NODE])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0xaCFEb570426e260Eb930971FE528c8014f1002a0',  # old GP safe, singleton frozen post-hack
    '0x9E0D8c9ff04F58e8D4053b78d33e582D8aCc8c44',  # new GP safe
]])
def test_gnosis_pay_safe_admins_recovers_frozen_safe(
        gnosis_manager_connect_at_start: list[tuple],
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list[str],
) -> None:
    """Both a new Gnosis Pay safe and an old one whose singleton was frozen by Gnosis Pay's
    post-hack migration must be recognized. The frozen old safe's getOwners()/
    getModulesPaginated() return empty, so the on-chain helper sees no admins and we have to
    recover them from the proxy's own storage. Hits the real chain on purpose - to be VCR'd
    later.
    """
    gnosis_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
    wait_until_all_nodes_connected(
        connect_at_start=gnosis_manager_connect_at_start,
        evm_inquirer=gnosis_inquirer,
    )
    old_safe, new_safe = gnosis_accounts
    admins = gnosis_inquirer.get_safe_admins_for_addresses(
        [string_to_evm_address(old_safe), string_to_evm_address(new_safe)],
    )
    assert {address: sorted(found) for address, found in admins.items()} == {
        old_safe: sorted([  # recovered from proxy storage since the singleton is frozen
            '0x34f40d7BdbFC99d27B3a596F0D1F3891DB415B03',
            '0x37f18A82493cdF80675fF01e58c1A1b39637cf50',
            '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',
        ]),
        new_safe: ['0x34f40d7BdbFC99d27B3a596F0D1F3891DB415B03'],  # resolved by the helper
    }
