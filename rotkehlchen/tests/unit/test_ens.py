import warnings as test_warnings

import pytest

from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.tests.utils.ens import (
    ENS_BRUNO,
    ENS_BRUNO_BTC_BYTES,
    ENS_BRUNO_ETH_ADDR,
    ENS_BRUNO_SUBSTRATE_PUBLIC_KEY,
)
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_TEST_PARAMETERS,
    wait_until_all_nodes_connected,
)
from rotkehlchen.typing import SupportedBlockchain


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_ens_lookup(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    """Test that ENS lookup works. Both with etherscan and with querying a real node"""
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_manager)
    result = ethereum_manager.ens_lookup('api.zerion.eth', call_order=call_order)
    assert result is not None
    if result != ZERION_ADAPTER_ADDRESS:
        test_warnings.warn(UserWarning('Zerion Adapter registry got an update'))

    result = ethereum_manager.ens_lookup('rotki.eth', call_order=call_order)
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    result = ethereum_manager.ens_lookup('ishouldprobablynotexist.eth', call_order=call_order)
    assert result is None

    result = ethereum_manager.ens_lookup('dsadsad', call_order=call_order)
    assert result is None


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_ens_lookup_multichain(
        ethereum_manager,
        call_order,
        ethereum_manager_connect_at_start,
):
    """Tests that ENS multichain lookup works as expected.

    Testing ENS domain is 'bruno.eth' from Kusama documention (it shouldn't change)
    https://app.ens.domains/name/bruno.eth
    """
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_manager)
    # Test default Ethereum
    result = ethereum_manager.ens_lookup(ENS_BRUNO, call_order=call_order)
    assert result == ENS_BRUNO_ETH_ADDR

    # Test blockchain Ethereum (defaults to 'addr(bytes32)')
    result = ethereum_manager.ens_lookup(
        ENS_BRUNO,
        call_order=call_order,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    assert result == ENS_BRUNO_ETH_ADDR

    # Test blockchain Bitcoin
    result = ethereum_manager.ens_lookup(
        ENS_BRUNO,
        call_order=call_order,
        blockchain=SupportedBlockchain.BITCOIN,
    )
    assert result == ENS_BRUNO_BTC_BYTES

    # Test blockchain Kusama
    result = ethereum_manager.ens_lookup(
        ENS_BRUNO,
        call_order=call_order,
        blockchain=SupportedBlockchain.KUSAMA,
    )
    assert result == ENS_BRUNO_SUBSTRATE_PUBLIC_KEY
