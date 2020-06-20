import warnings as test_warnings

import pytest

from rotkehlchen.tests.utils.ethereum import ETHEREUM_TEST_PARAMETERS


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_ens_lookup(ethereum_manager):
    """Test that ENS lookup works. Both with etherscan and with querying a real node"""
    result = ethereum_manager.ens_lookup('api.zerion.eth')
    assert result is not None
    if result != '0x06FE76B2f432fdfEcAEf1a7d4f6C3d41B5861672':
        test_warnings.warn(UserWarning('Zerion Adapter registry got an update'))

    result = ethereum_manager.ens_lookup('rotki.eth')
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    result = ethereum_manager.ens_lookup('ishouldprobablynotexist.eth')
    assert result is None

    result = ethereum_manager.ens_lookup('dsadsad')
    assert result is None
