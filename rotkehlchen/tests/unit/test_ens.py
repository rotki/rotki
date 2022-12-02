import warnings as test_warnings
from unittest.mock import patch

import pytest
from eth_utils import to_checksum_address

from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import InputError
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
from rotkehlchen.types import SupportedBlockchain


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_ens_lookup(ethereum_inquirer, call_order, ethereum_manager_connect_at_start):
    """Test that ENS lookup works. Both with etherscan and with querying a real node"""
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_inquirer)
    result = ethereum_inquirer.ens_lookup('api.zerion.eth', call_order=call_order)
    assert result is not None
    if result != ZERION_ADAPTER_ADDRESS:
        test_warnings.warn(UserWarning('Zerion Adapter registry got an update'))

    result = ethereum_inquirer.ens_lookup('rotki.eth', call_order=call_order)
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'

    # Test invalid name
    with pytest.raises(InputError) as e:
        ethereum_inquirer.ens_lookup('fl00_id.loopring.eth', call_order=call_order)
    assert "fl00_id.loopring.eth is an invalid name, because Codepoint U+005F not allowed at position 5 in 'fl00_id.loopring.eth'" in str(e.value)  # noqa: E501

    result = ethereum_inquirer.ens_lookup('ishouldprobablynotexist.eth', call_order=call_order)
    assert result is None

    result = ethereum_inquirer.ens_lookup('dsadsad', call_order=call_order)
    assert result is None


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_ens_lookup_multichain(
        ethereum_inquirer,
        call_order,
        ethereum_manager_connect_at_start,
):
    """Tests that ENS multichain lookup works as expected.

    Testing ENS domain is 'bruno.eth' from Kusama documentation (it shouldn't change)
    https://app.ens.domains/name/bruno.eth
    """
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_inquirer)
    # Test default Ethereum
    result = ethereum_inquirer.ens_lookup(ENS_BRUNO, call_order=call_order)
    assert result == ENS_BRUNO_ETH_ADDR

    # Test blockchain Ethereum (defaults to 'addr(bytes32)')
    result = ethereum_inquirer.ens_lookup(
        ENS_BRUNO,
        call_order=call_order,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    assert result == ENS_BRUNO_ETH_ADDR

    # Test blockchain Bitcoin
    result = ethereum_inquirer.ens_lookup(
        ENS_BRUNO,
        call_order=call_order,
        blockchain=SupportedBlockchain.BITCOIN,
    )
    assert result == ENS_BRUNO_BTC_BYTES

    # Test blockchain Kusama
    result = ethereum_inquirer.ens_lookup(
        ENS_BRUNO,
        call_order=call_order,
        blockchain=SupportedBlockchain.KUSAMA,
    )
    assert result == ENS_BRUNO_SUBSTRATE_PUBLIC_KEY


def test_ens_reverse_lookup(ethereum_inquirer):
    """This test could be flaky because it assumes
        that all used ens names exist
    """
    call_contract_patch = patch.object(
        ethereum_inquirer,
        'call_contract',
        wraps=ethereum_inquirer.call_contract,
    )
    # Mocking addresses per reverse ens query to check that chunking works correctly
    # We do 2 requests - first without splitting in chunks and in the second one addresses
    # should be split. We confirm it by checking call_count attribute of the call contract patch.
    addrs_in_chunk_patch = patch(
        target='rotkehlchen.chain.ethereum.node_inquirer.MAX_ADDRESSES_IN_REVERSE_ENS_QUERY',
        new=2,
    )
    with addrs_in_chunk_patch, call_contract_patch as call_contract_mock:
        reversed_addr_0 = to_checksum_address('0x71C7656EC7ab88b098defB751B7401B5f6d8976F')
        reversed_addr_1 = ethereum_inquirer.ens_lookup('lefteris.eth')
        expected = {reversed_addr_0: None, reversed_addr_1: 'lefteris.eth'}
        assert ethereum_inquirer.ens_reverse_lookup([reversed_addr_0, reversed_addr_1]) == expected
        assert call_contract_mock.call_count == 1

    with addrs_in_chunk_patch, call_contract_patch as call_contract_mock:
        reversed_addr_2 = ethereum_inquirer.ens_lookup('abc.eth')
        reversed_addr_3 = ethereum_inquirer.ens_lookup('rotki.eth')
        # reversed_addr_4 has not configured ens name resolution properly
        reversed_addr_4 = string_to_evm_address('0x5b2Ed2eF8F480cC165A600aC451D9D9Ebf521e94')
        expected = {reversed_addr_2: 'abc.eth', reversed_addr_3: 'rotki.eth', reversed_addr_4: None}  # noqa: E501
        queried_ens_names = ethereum_inquirer.ens_reverse_lookup(
            [reversed_addr_2, reversed_addr_3, reversed_addr_4],
        )
        assert queried_ens_names == expected
        assert call_contract_mock.call_count == 2
