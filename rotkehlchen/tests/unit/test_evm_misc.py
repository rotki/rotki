import typing

import pytest

from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.evm.constants import EVM_ADDRESS_REGEX
from rotkehlchen.chain.evm.decoding.weth.constants import (
    CHAIN_ID_TO_WETH_MAPPING,
    CHAINS_WITHOUT_NATIVE_ETH,
)
from rotkehlchen.chain.evm.types import asset_id_is_evm_token, string_to_evm_address
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChainID


def test_asset_id_is_evm_token():
    result = asset_id_is_evm_token('eip155:1/erc20:0x0F5D2fB29fb7d3CFeE444a200298f468908cC942')
    assert result == (
        ChainID.ETHEREUM,
        string_to_evm_address('0x0F5D2fB29fb7d3CFeE444a200298f468908cC942'),
    )
    result = asset_id_is_evm_token('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607')
    assert result == (
        ChainID.OPTIMISM,
        string_to_evm_address('0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
    )
    result = asset_id_is_evm_token('eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88')
    assert result == (
        ChainID.ETHEREUM,
        string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
    )

    assert asset_id_is_evm_token('ETH') is None
    assert asset_id_is_evm_token('BTC') is None
    assert asset_id_is_evm_token('eip155:125/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88') is None  # noqa: E501


def test_address_regex() -> None:
    cases: dict[str, bool] = {
        '0x0F5D2fB29fb7d3CFeE444a200298f468908cC942': True,  # address
        '0x9b675024d8648c3b590eff411fcf75a1199d10d1a3fe2ddbe50e166ce8b87cc9': False,  # transaction hash  # noqa: E501
        'https://etherscan.io/address/0x0F5D2fB29fb7d3CFeE444a200298f468908cC942': True,  # etherscan link of an address  # noqa: E501
        'https://etherscan.io/tx/0x9b675024d8648c3b590eff411fcf75a1199d10d1a3fe2ddbe50e166ce8b87cc9': False,  # etherscan link of a transaction  # noqa: E501
        '0x0F5D2fB29fb7d3CFeE444a200298f468908cC942a': False,  # invalid address length
        '0x0F5D2fB29fb7d3CFeE444a200298f468908zC942': False,  # invalid address characters
        '0x0F5D2fB29fb7d3CFeE444a200298f468908cC942 Note with address at the start': True,
        'Note with address in the end 0x0F5D2fB29fb7d3CFeE444a200298f468908cC942': True,
        'A full stop after the address 0x0F5D2fB29fb7d3CFeE444a200298f468908cC942.': True,
    }

    for case, expected_result in cases.items():
        assert (EVM_ADDRESS_REGEX.search(case) is not None) == expected_result


def test_weth_is_supported():
    """Check that weth is supported for all the evm chains with ETH"""
    assert (
        set(CHAIN_ID_TO_WETH_MAPPING.keys()) ==
        set(typing.get_args(SUPPORTED_CHAIN_IDS)) - CHAINS_WITHOUT_NATIVE_ETH
    )


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('base_accounts', [[make_evm_address()]])
@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_is_safe_proxy(blockchain: ChainsAggregator):
    assert blockchain.ethereum.node_inquirer.is_safe_proxy_or_eoa(  # EOA
        address=string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65'),
    ) is True
    assert blockchain.base.node_inquirer.is_safe_proxy_or_eoa(  # safe
        address=string_to_evm_address('0x9d25AdBcffE28923E619f4Af88ECDe732c985b63'),
    ) is True
    assert blockchain.ethereum.node_inquirer.is_safe_proxy_or_eoa(  # balanceScanner contract
        address=string_to_evm_address('0x54eCF3f6f61F63fdFE7c27Ee8A86e54899600C92'),
    ) is False
    assert blockchain.ethereum.node_inquirer.is_safe_proxy_or_eoa(  # old safe
        address=string_to_evm_address('0xd12745b5CA546A408a35e8C77d81Aa0a7526DE7b'),
    ) is True
