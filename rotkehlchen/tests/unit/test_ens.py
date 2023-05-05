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


@pytest.mark.parametrize('should_mock_web3', [True])
@pytest.mark.parametrize('ethereum_mock_data', [{
    'eth_call': {
        '0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e': {
            '0x0178b8bf59bf8936dba1550677fa0e3950bc703b90b92ab9423bfbced145233f4050bff6': {
                # getting resolver addr for api.zerion.eth
                'latest': '0x000000000000000000000000daaf96c344f63131acadd0ea35170e7892d3dfba',
            },
            '0x0178b8bfa92039d81cb82a6a9c69005ef09df58f6d692d7f28a09aa558d5a12655688e9b': {
                # getting resolver addr for rotki.eth
                'latest': '0x000000000000000000000000226159d592e2b063810a10ebf6dcbada94ed68b8',
            },
            '0x0178b8bf4a2f620499c726cf4ddce49f75d6144f224907afc459d76c3769c26091f0bc30': {
                # getting resolver addr for ishouldprobablynotexist.eth or dsadsad
                'latest': '0x0000000000000000000000000000000000000000000000000000000000000000',
            },
            '0x0178b8bfde0df0b6cfb5f37a4131be127532dd375bd06f0eb43f98ebc15a0460c3719953': {
                # getting resolver addr for ishouldprobablynotexist.eth or dsadsad
                'latest': '0x0000000000000000000000000000000000000000000000000000000000000000',
            },
        },
        '0xDaaF96c344f63131acadD0Ea35170E7892d3dfBA': {
            '0x3b3b57de59bf8936dba1550677fa0e3950bc703b90b92ab9423bfbced145233f4050bff6': {
                # calling addr() on resolver for api.zerion.eth
                'latest': '0x00000000000000000000000006fe76b2f432fdfecaef1a7d4f6c3d41b5861672',
            },
        },
        '0x226159d592E2b063810a10Ebf6dcbADA94Ed68b8': {
            '0x3b3b57dea92039d81cb82a6a9c69005ef09df58f6d692d7f28a09aa558d5a12655688e9b': {
                # calling addr() on resolver for rotki.eth
                'latest': '0x0000000000000000000000009531c059098e3d194ff87febb587ab07b30b1306',
            },
        },
    },
}])
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


@pytest.mark.parametrize('should_mock_web3', [True])
@pytest.mark.parametrize('ethereum_mock_data', [{
    'eth_call': {
        '0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e': {
            '0x0178b8bf9de0b76f3b87380f0bcb9e41b403c69b88b01fbeaf785e83f38a6879902af71b': {
                # getting resolver addr for bruno.eth
                'latest': '0x0000000000000000000000004976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41',
            },
        },
        '0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41': {
            '0x3b3b57de9de0b76f3b87380f0bcb9e41b403c69b88b01fbeaf785e83f38a6879902af71b': {
                # calling addr() on resolver for bruno.eth
                'latest': '0x000000000000000000000000b9b8ef61b7851276b0239757a039d54a23804cbb',
            },
            '0xf1cb7e069de0b76f3b87380f0bcb9e41b403c69b88b01fbeaf785e83f38a6879902af71b0000000000000000000000000000000000000000000000000000000000000000': {  # noqa: E501
                # calling addr() on resolver for bruno.eth and coin type Bitcoin
                'latest': '0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001976a9147f1fff38da2809b9368262284e0608dfb5c4537988ac00000000000000',  # noqa: E501
            },
            '0xf1cb7e069de0b76f3b87380f0bcb9e41b403c69b88b01fbeaf785e83f38a6879902af71b00000000000000000000000000000000000000000000000000000000000001b2': {  # noqa: E501
                # calling addr() on resolver for bruno.eth and coin type Kusama
                'latest': '0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000200aff6865635ae11013a83835c019d44ec3f865145943f487ae82a8e7bed3a66b',  # noqa: E501
            },
        },
    },
}])
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


@pytest.mark.parametrize('should_mock_web3', [True])
@pytest.mark.parametrize('ethereum_mock_data', [{
    'eth_call': {
        '0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e': {
            '0x0178b8bfe4ce152682c62d25dbc668723afbc7d9b6baa21b5c1e9a19f94213198a2e5efb': {
                # getting resolver addr for lefteris.eth
                'latest': '0x0000000000000000000000004976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41',
            },
            '0x0178b8bf9f5cd92e2589fadd191e7e7917b9328d03dc84b7a67773db26efb7d0a4635677': {
                # getting resolver addr for abc.eth
                'latest': '0x0000000000000000000000004976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41',
            },
            '0x0178b8bfa92039d81cb82a6a9c69005ef09df58f6d692d7f28a09aa558d5a12655688e9b': {
                # getting resolver addr for rotki.eth
                'latest': '0x000000000000000000000000226159d592e2b063810a10ebf6dcbada94ed68b8',
            },
        },
        '0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41': {
            '0x3b3b57dee4ce152682c62d25dbc668723afbc7d9b6baa21b5c1e9a19f94213198a2e5efb': {
                # calling addr() on resolver for lefteris.eth
                'latest': '0x0000000000000000000000002b888954421b424c5d3d9ce9bb67c9bd47537d12',
            },
            '0x3b3b57de9f5cd92e2589fadd191e7e7917b9328d03dc84b7a67773db26efb7d0a4635677': {
                # calling addr() on resolver for abc.eth
                'latest': '0x000000000000000000000000a4b73b39f73f73655e9fdc5d167c21b3fa4a1ed6',
            },
        },
        '0x3671aE578E63FdF66ad4F3E12CC0c0d71Ac7510C': {
            '0xcbf8b66c0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000200000000000000000000000071c7656ec7ab88b098defb751b7401b5f6d8976f0000000000000000000000002b888954421b424c5d3d9ce9bb67c9bd47537d12': {  # noqa: E501
                # getNames() on ens reverse records for
                # '0x71C7656EC7ab88b098defB751B7401B5f6d8976F',
                # '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
                'latest': '0x00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c6c656674657269732e6574680000000000000000000000000000000000000000',  # noqa: E501
            },
            '0xcbf8b66c00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000a4b73b39f73f73655e9fdc5d167c21b3fa4a1ed60000000000000000000000009531c059098e3d194ff87febb587ab07b30b1306': {  # noqa: E501
                # getNames() on ens reverse records for
                # '0xA4b73b39F73F73655e9fdC5D167c21b3fA4A1eD6',
                # '0x9531C059098e3d194fF87FebB587aB07B30B1306'
                'latest': '0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000076162632e657468000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000009726f746b692e6574680000000000000000000000000000000000000000000000',  # noqa: E501
            },
            '0xcbf8b66c000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000005b2ed2ef8f480cc165a600ac451d9d9ebf521e94': {  # noqa: E501
                # getNames() on ens reverse records for
                # '0x5b2Ed2eF8F480cC165A600aC451D9D9Ebf521e94'
                'latest': '0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000',  # noqa: E501
            },
        },
        '0x226159d592E2b063810a10Ebf6dcbADA94Ed68b8': {
            '0x3b3b57dea92039d81cb82a6a9c69005ef09df58f6d692d7f28a09aa558d5a12655688e9b': {
                # calling addr() on resolver for rotki.eth
                'latest': '0x0000000000000000000000009531c059098e3d194ff87febb587ab07b30b1306',
            },
        },
    },
}])
def test_ens_reverse_lookup(ethereum_inquirer):
    """This test could be flaky because it assumes
        that all used ens names exist
    """
    call_contract_patch = patch.object(
        ethereum_inquirer,
        'call_contract',
        wraps=ethereum_inquirer.call_contract,
    )
    # The patch is just to to check that chunking works correctly
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
        assert call_contract_mock.call_count == 2

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
        assert call_contract_mock.call_count == 4
