import typing
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.evm.constants import EVM_ADDRESS_REGEX
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.weth.constants import (
    CHAIN_ID_TO_WETH_MAPPING,
    CHAINS_WITHOUT_NATIVE_ETH,
)
from rotkehlchen.chain.evm.types import (
    NodeName,
    WeightedNode,
    asset_id_is_evm_token,
    string_to_evm_address,
)
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import RemoteError, RequestTooLargeError
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_WEB3_AND_ETHERSCAN_TEST_PARAMETERS,
    wait_until_all_nodes_connected,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChainID, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer


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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_manager_connect_at_start', [(WeightedNode(
    node_info=NodeName(
        name='gnosischain',
        endpoint='https://rpc.gnosischain.com',
        owned=False,
        blockchain=SupportedBlockchain.GNOSIS,
    ),
    active=True,
    weight=ONE,
),)])
def test_multicall_error_retry(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_manager_connect_at_start: list[tuple],
):
    """Test multicall retries with smaller chunks on errors."""
    wait_until_all_nodes_connected(gnosis_manager_connect_at_start, gnosis_inquirer)

    contract = EvmContract(
        address=(wxdai := string_to_evm_address('0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d')),
        abi=gnosis_inquirer.contracts.erc20_abi,
        deployed_block=0,
    )
    calls = [(wxdai, contract.encode(method_name='symbol')) for _ in range(4)]

    call_count = 0
    original_call_contract = gnosis_inquirer.call_contract

    def mock_call_contract(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RequestTooLargeError('Multicall failed')
        return original_call_contract(*args, **kwargs)

    with patch.object(gnosis_inquirer, 'call_contract', side_effect=mock_call_contract):
        result = gnosis_inquirer.multicall(calls=calls)

    # 1 failed (large chunk) + 2 successful (chunk_size=3, 4 calls = 2 chunks)
    assert len(result) == 4
    assert call_count == 3

    # set `_multicall_failed_length` and see that is respected.
    estimated_length = sum(len(call[1]) for call in calls)
    assert gnosis_inquirer._multicall_failed_length.get('nodes') == estimated_length

    call_count = 0

    def mock_call_contract_no_fail(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_call_contract(*args, **kwargs)

    with patch.object(gnosis_inquirer, 'call_contract', side_effect=mock_call_contract_no_fail):
        result = gnosis_inquirer.multicall(calls=calls)

    # proactive chunk_size=3 from start (4 calls = 2 chunks), no retry
    assert len(result) == 4
    assert call_count == 2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(*ETHEREUM_WEB3_AND_ETHERSCAN_TEST_PARAMETERS)
def test_query_raises_request_too_large_when_gas_limit_seen(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_manager_connect_at_start: list[tuple],
) -> None:
    """Test that _query raises RequestTooLargeError when any node returns gas limit error,
    even if later nodes fail with different errors."""
    wait_until_all_nodes_connected(ethereum_manager_connect_at_start, ethereum_inquirer)

    call_count = 0

    def mock_method(web3, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RemoteError('out of gas')
        raise RemoteError('connection timeout')

    call_order = ethereum_inquirer.default_call_order()
    with pytest.raises(RequestTooLargeError):
        ethereum_inquirer._query(method=mock_method, call_order=call_order)

    assert call_count == len(call_order)
