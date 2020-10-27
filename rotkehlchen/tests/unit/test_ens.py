import os
import warnings as test_warnings

import pytest

from rotkehlchen.chain.ethereum.zerion import ZERION_ADAPTER_ADDRESS
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_TEST_PARAMETERS,
    wait_until_all_nodes_connected,
)


@pytest.mark.skipif(
    'GITHUB_WORKFLOW' in os.environ,
    reason='For some reason connecting to infura fails in Github actions for this test',
)
@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_ens_lookup(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    """Test that ENS lookup works. Both with etherscan and with querying a real node"""
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_manager)
    result = ethereum_manager.ens_lookup('api.zerion.eth', call_order)
    assert result is not None
    if result != ZERION_ADAPTER_ADDRESS:
        test_warnings.warn(UserWarning('Zerion Adapter registry got an update'))

    result = ethereum_manager.ens_lookup('rotki.eth', call_order)
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    result = ethereum_manager.ens_lookup('ishouldprobablynotexist.eth', call_order)
    assert result is None

    result = ethereum_manager.ens_lookup('dsadsad', call_order)
    assert result is None
