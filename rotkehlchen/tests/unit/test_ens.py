from unittest.mock import MagicMock, patch

import pytest
from eth_utils import to_checksum_address

from rotkehlchen.chain.ethereum.constants import EVM_INDEXERS_NODE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.mixins.rpc_nodes import RPCNode
from rotkehlchen.errors.misc import BlockchainQueryError, InputError
from rotkehlchen.tests.utils.ens import (
    ENS_BRUNO,
    ENS_BRUNO_BTC_BYTES,
    ENS_BRUNO_ETH_ADDR,
    ENS_BRUNO_SUBSTRATE_PUBLIC_KEY,
)
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_TEST_PARAMETERS,
    INFURA_ETH_NODE,
    wait_until_all_nodes_connected,
)
from rotkehlchen.types import SupportedBlockchain


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_ens_lookup(ethereum_inquirer, call_order, ethereum_manager_connect_at_start):
    """Test that ENS lookup works. Both with etherscan and with querying a real node"""
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_inquirer)
    result = ethereum_inquirer.ens_lookup('api.zerion.eth', call_order=call_order)
    assert result is not None
    result = ethereum_inquirer.ens_lookup('rotki.eth', call_order=call_order)
    assert result == '0x9531C059098e3d194fF87FebB587aB07B30B1306'

    # Test invalid name
    with pytest.raises(InputError) as e:
        ethereum_inquirer.ens_lookup('fl00_id.loopring.eth', call_order=call_order)
    assert "Underscores '_' may only occur at the start of a label: 'fl00_id'" in str(e.value)

    result = ethereum_inquirer.ens_lookup('ishouldprobablynotexist.eth', call_order=call_order)
    assert result is None
    result = ethereum_inquirer.ens_lookup('dsadsad', call_order=call_order)
    assert result is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_ens_reverse_lookup(ethereum_inquirer):
    """This test could be flaky because it assumes
        that all used ens names exist
    """
    addrs_in_chunk_patch = patch(
        target='rotkehlchen.chain.ethereum.node_inquirer.MAX_ADDRESSES_IN_REVERSE_ENS_QUERY',
        new=2,
    )
    with addrs_in_chunk_patch:
        reversed_addr_0 = to_checksum_address('0x71C7656EC7ab88b098defB751B7401B5f6d8976F')
        reversed_addr_1 = ethereum_inquirer.ens_lookup('lefteris.eth')
        expected = {reversed_addr_0: None, reversed_addr_1: 'lefteris.eth'}
        assert ethereum_inquirer.ens_reverse_lookup([reversed_addr_0, reversed_addr_1]) == expected

    with addrs_in_chunk_patch:
        reversed_addr_2 = ethereum_inquirer.ens_lookup('abc.eth')
        reversed_addr_3 = ethereum_inquirer.ens_lookup('rotki.eth')
        # reversed_addr_4 has not configured ens name resolution properly
        reversed_addr_4 = string_to_evm_address('0x5b2Ed2eF8F480cC165A600aC451D9D9Ebf521e94')
        expected = {reversed_addr_2: 'abc.eth', reversed_addr_3: 'rotki.eth', reversed_addr_4: None}  # noqa: E501
        queried_ens_names = ethereum_inquirer.ens_reverse_lookup(
            [reversed_addr_2, reversed_addr_3, reversed_addr_4],
        )
        assert queried_ens_names == expected


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_get_ens_resolver_addr_uses_rpc_nodes(
        ethereum_inquirer,
        ethereum_manager_connect_at_start,
):
    """Test that the ENS resolver lookup goes through the RPC nodes and not the indexers"""
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_inquirer)
    with patch.object(
        ethereum_inquirer,
        '_call_contract_indexers',
        side_effect=AssertionError('The indexers should not be queried'),
    ):
        resolver_addr, normal_name = ethereum_inquirer.get_ens_resolver_addr('rotki.eth')
        assert resolver_addr is not None
        assert normal_name == 'rotki.eth'
        # an unresolvable name returns no resolver, instead of raising
        assert ethereum_inquirer.get_ens_resolver_addr('dsadsad') == (None, None)

        with pytest.raises(InputError):
            ethereum_inquirer.get_ens_resolver_addr('fl00_id.loopring.eth')


def test_get_ens_resolver_addr_falls_back_on_rpc_error(ethereum_inquirer):
    """Test that an RPC error during the ENS resolver lookup is not treated as
    an unresolvable name, but the node is marked as failed and the next source is queried"""
    ethereum_inquirer.rpc_mapping[INFURA_ETH_NODE.node_info] = RPCNode(
        rpc_client=(failing_web3 := MagicMock()),
        is_pruned=False,
        is_archive=True,
    )

    def mock_call_contract(web3, **kwargs):
        if web3 is failing_web3:
            raise BlockchainQueryError('Error doing call on contract: transient RPC error')
        return '0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63', b'', 0

    with (
        patch.object(
            ethereum_inquirer,
            'default_call_order',
            return_value=[INFURA_ETH_NODE, EVM_INDEXERS_NODE],
        ),
        patch.object(
            ethereum_inquirer,
            '_call_contract',
            autospec=True,
            side_effect=mock_call_contract,
        ) as call_contract_mock,
        patch.object(
            ethereum_inquirer,
            'mark_node_success',
            wraps=ethereum_inquirer.mark_node_success,
        ) as mark_success_mock,
    ):
        assert ethereum_inquirer.get_ens_resolver_addr('rotki.eth') == (
            '0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63',
            'rotki.eth',
        )

    assert [call.args[0] for call in call_contract_mock.call_args_list] == [failing_web3, None]
    mark_success_mock.assert_called_once_with(EVM_INDEXERS_NODE.node_info)
