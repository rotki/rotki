from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.tests.utils.arbitrum_one import (
    ARBITRUM_ONE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED,
)
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer


@pytest.mark.vcr
@pytest.mark.parametrize(*ARBITRUM_ONE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED)
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xCace5b3c29211740E595850E80478416eE77cA21']])  # to connect to nodes  # noqa: E501
def test_arbitrum_one_nodes_prune_and_archive_status(
        arbitrum_one_manager_connect_at_start: list[tuple],
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
):
    """Checks that connecting to a set of Arbitrum One nodes, the capabilities of those nodes
    are known and stored. It tests the nodes one by one to avoid the randomness of the connections
    to the nodes while running with the VCR cassettes.
    """
    arbitrum_one_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
    wait_until_all_nodes_connected(
        connect_at_start=arbitrum_one_manager_connect_at_start,
        evm_inquirer=arbitrum_one_inquirer,
    )
    for node_name, web3_node in arbitrum_one_inquirer.web3_mapping.items():
        if node_name.endpoint == 'https://arbitrum-one-archive.allthatnode.com':
            assert not web3_node.is_pruned
            assert web3_node.is_archive
        elif node_name.endpoint == 'https://arbitrum.blockpi.network/v1/rpc/public':
            assert not web3_node.is_pruned
            # not checking for archive here, as some times it is and some not
        # TODO add a check for a pruned node.
        # TODO All these calls should be mocked. Can't rely on a remote always being pruned, full or archive for a CI test  # noqa: E501
        else:
            raise AssertionError(f'Unknown node {node_name} encountered.')

    assert len(arbitrum_one_inquirer.web3_mapping) == len(arbitrum_one_manager_connect_at_start)


def test_block_by_time_close_to_genesis(arbitrum_one_inquirer):
    """Checks that etherscan handles block number by time query correctly for a timestamp
    very close to genesis"""
    result = arbitrum_one_inquirer.get_blocknumber_by_time(1622243344)
    assert result == 1


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_multicall_with_etherscan_fallback(arbitrum_one_inquirer):
    """Test that multicall works and can fallback to etherscan with reduced chunk size"""
    contract = EvmContract(
        address=(usdc_arbitrum := string_to_evm_address('0xaf88d065e77c8cC2239327C5EDb3A432268e5831')),  # noqa: E501
        abi=arbitrum_one_inquirer.contracts.erc20_abi,
        deployed_block=0,
    )
    call_count = 0
    original_query = arbitrum_one_inquirer._query

    def count_calls(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_query(*args, **kwargs)

    methods = ['totalSupply', 'name', 'symbol', 'decimals']
    with patch.object(arbitrum_one_inquirer, '_query', side_effect=count_calls):
        assert (result := arbitrum_one_inquirer.multicall(calls=(test_calls := [
            (usdc_arbitrum, contract.encode(method_name=method))
            for method in methods
        ]))) is not None

    assert len(result) == len(test_calls)
    # Expected 3 calls: Call #1 fails on non-etherscan nodes (empty call order),
    # Call #2 succeeds on etherscan with first chunk (3 calls: totalSupply, name, symbol),
    # Call #3 succeeds on etherscan with second chunk (1 call: decimals)
    assert call_count == 3

    decoded = [contract.decode(result[i], methods[i])[0] for i in range(len(methods))]
    total_supply, name, symbol, decimals = decoded
    assert total_supply == 6800074379367774
    assert name == 'USD Coin'
    assert symbol == 'USDC'
    assert decimals == 6
