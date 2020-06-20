import warnings as test_warnings

import pytest

from rotkehlchen.chain.ethereum.manager import EthereumManager


@pytest.mark.parametrize('params', [
    {'endpoint': '', 'connect': False},
    # For real node querying let's use blockscout
    {'endpoint': 'https://mainnet-nethermind.blockscout.com', 'connect': True}])
def test_ens_lookup(etherscan, messages_aggregator, params):
    """Test that ENS lookup works. Both with etherscan and with querying a real node"""
    ethereum = EthereumManager(
        ethrpc_endpoint='',
        etherscan=etherscan,
        msg_aggregator=messages_aggregator,
        attempt_connect=False,
    )
    result = ethereum.ens_lookup('api.zerion.eth')
    assert result is not None
    if result != '0x06FE76B2f432fdfEcAEf1a7d4f6C3d41B5861672':
        test_warnings.warn(UserWarning('Zerion Adapter registry got an update'))

    result = ethereum.ens_lookup('rotki.eth')
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    result = ethereum.ens_lookup('ishouldprobablynotexist.eth')
    assert result is None

    result = ethereum.ens_lookup('dsadsad')
    assert result is None
