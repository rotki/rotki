import typing
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

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
from rotkehlchen.chain.mixins.rpc_nodes import RPCNode
from rotkehlchen.constants import ONE
from rotkehlchen.errors.misc import RemoteError, RequestTooLargeError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_evm_transaction
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_WEB3_AND_ETHERSCAN_TEST_PARAMETERS,
    wait_until_all_nodes_connected,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ChainID,
    EvmTransaction,
    SupportedBlockchain,
    Timestamp,
)

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


def test_query_skips_rate_limited_nodes_temporarily(
        ethereum_inquirer: 'EthereumInquirer',
) -> None:
    first_node = WeightedNode(
        node_info=NodeName(
            name='rate_limited',
            endpoint='https://rate-limited.example',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        active=True,
        weight=ONE,
    )
    second_node = WeightedNode(
        node_info=NodeName(
            name='healthy',
            endpoint='https://healthy.example',
            owned=False,
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
        active=True,
        weight=ONE,
    )
    call_order = [first_node, second_node]
    ethereum_inquirer.rate_limited_nodes.clear()
    ethereum_inquirer.rpc_mapping[first_node.node_info] = RPCNode(
        rpc_client=first_node.node_info.endpoint,  # type: ignore[arg-type]
        is_pruned=False,
        is_archive=True,
    )
    ethereum_inquirer.rpc_mapping[second_node.node_info] = RPCNode(
        rpc_client=second_node.node_info.endpoint,  # type: ignore[arg-type]
        is_pruned=False,
        is_archive=True,
    )
    first_response = requests.Response()
    first_response.status_code = 429
    first_response.headers['Retry-After'] = '120'
    first_error = requests.exceptions.HTTPError(response=first_response)
    call_sequence: list[str] = []

    def mock_method(web3: str) -> str:
        call_sequence.append(web3)
        if web3 == first_node.node_info.endpoint:
            raise first_error
        return 'ok'

    assert ethereum_inquirer._query(method=mock_method, call_order=call_order) == 'ok'
    assert call_sequence == [first_node.node_info.endpoint, second_node.node_info.endpoint]
    assert first_node.node_info.endpoint in ethereum_inquirer.rate_limited_nodes

    call_sequence.clear()
    assert ethereum_inquirer._query(method=mock_method, call_order=call_order) == 'ok'
    assert call_sequence == [second_node.node_info.endpoint]


def test_default_call_order_handles_non_normalized_weights(
        ethereum_inquirer: 'EthereumInquirer',
) -> None:
    call_order_nodes = [
        WeightedNode(
            identifier=1,
            node_info=NodeName(
                name='owned',
                endpoint='https://owned.example',
                owned=True,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
            active=True,
            weight=FVal('0.01'),
        ),
        WeightedNode(
            identifier=2,
            node_info=NodeName(
                name='heavy',
                endpoint='https://heavy.example',
                owned=False,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
            active=True,
            weight=FVal('10'),
        ),
        WeightedNode(
            identifier=3,
            node_info=NodeName(
                name='medium',
                endpoint='https://medium.example',
                owned=False,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
            active=True,
            weight=FVal('3'),
        ),
        WeightedNode(
            identifier=4,
            node_info=NodeName(
                name='invalid-negative',
                endpoint='https://invalid-negative.example',
                owned=False,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
            active=True,
            weight=FVal('-1'),
        ),
    ]
    expected_names = {node.node_info.name for node in call_order_nodes}
    with patch.object(ethereum_inquirer.database, 'get_rpc_nodes', return_value=call_order_nodes):
        for _ in range(10):
            ordered = ethereum_inquirer.default_call_order(skip_indexers=True)
            assert len(ordered) == len(call_order_nodes)
            assert {node.node_info.name for node in ordered} == expected_names
            assert ordered[0].node_info.name == 'owned'


def test_rpc_nodes_cache_invalidated_on_mutations(database) -> None:
    blockchain = SupportedBlockchain.ETHEREUM
    added_endpoint = 'https://cache-add.example'
    updated_endpoint = 'https://cache-update.example'
    with patch.object(
            database,
            '_query_rpc_nodes_from_db',
            wraps=database._query_rpc_nodes_from_db,
    ) as query_patch:
        database.get_rpc_nodes(blockchain=blockchain, only_active=True)
        database.get_rpc_nodes(blockchain=blockchain, only_active=True)
        assert query_patch.call_count == 1

        database.add_rpc_node(WeightedNode(
            node_info=NodeName(
                name='cache-add',
                endpoint=added_endpoint,
                owned=False,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
            active=True,
            weight=FVal('0.01'),
        ))
        nodes_after_add = database.get_rpc_nodes(blockchain=blockchain, only_active=True)
        assert query_patch.call_count == 2
        added_node = next(
            node for node in nodes_after_add
            if node.node_info.endpoint == added_endpoint
        )

        database.update_rpc_node(WeightedNode(
            identifier=added_node.identifier,
            node_info=NodeName(
                name='cache-update',
                endpoint=updated_endpoint,
                owned=False,
                blockchain=SupportedBlockchain.ETHEREUM,
            ),
            active=True,
            weight=FVal('0.02'),
        ))
        nodes_after_update = database.get_rpc_nodes(blockchain=blockchain, only_active=True)
        assert query_patch.call_count == 3
        assert added_endpoint not in {node.node_info.endpoint for node in nodes_after_update}
        assert updated_endpoint in {node.node_info.endpoint for node in nodes_after_update}

        database.delete_rpc_node(identifier=added_node.identifier, blockchain=blockchain)
        nodes_after_delete = database.get_rpc_nodes(blockchain=blockchain, only_active=True)
        assert query_patch.call_count == 4
        assert updated_endpoint not in {node.node_info.endpoint for node in nodes_after_delete}


def test_get_transactions_populates_block_timestamp_cache(
        ethereum_inquirer: 'EthereumInquirer',
) -> None:
    tx = EvmTransaction(
        tx_hash=make_evm_tx_hash(),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1710000000),
        block_number=123456,
        from_address=make_evm_address(),
        to_address=make_evm_address(),
        value=0,
        gas=21000,
        gas_price=100,
        gas_used=21000,
        input_data=b'',
        nonce=1,
    )
    with patch.object(ethereum_inquirer, '_try_indexers_iterable', return_value=iter([[tx]])):
        result = list(ethereum_inquirer.get_transactions(
            account=make_evm_address(),
            action='txlist',
        ))

    assert result == [[tx]]
    assert ethereum_inquirer.block_to_timestamp_cache.get(tx.block_number) == tx.timestamp


def test_get_token_transaction_hashes_populates_block_timestamp_cache(
        ethereum_inquirer: 'EthereumInquirer',
) -> None:
    tx_hash = make_evm_tx_hash()
    block_number = 654321
    timestamp = Timestamp(1712222222)
    with patch.object(
            ethereum_inquirer,
            '_try_indexers_iterable',
            return_value=iter([[(tx_hash, timestamp, block_number)]]),
    ):
        result = list(ethereum_inquirer.get_token_transaction_hashes(
            account=make_evm_address(),
        ))

    assert result == [[tx_hash]]
    assert ethereum_inquirer.block_to_timestamp_cache.get(block_number) == timestamp


def test_deserialize_evm_transaction_uses_cached_block_timestamp(
        ethereum_inquirer: 'EthereumInquirer',
) -> None:
    block_number = 999
    expected_timestamp = Timestamp(1711111111)
    ethereum_inquirer.cache_block_timestamp(
        block_number=block_number,
        timestamp=expected_timestamp,
    )
    tx_data = {
        'hash': str(make_evm_tx_hash()),
        'blockNumber': str(block_number),
        'from': make_evm_address(),
        'to': make_evm_address(),
        'value': '0',
        'gas': '21000',
        'gasPrice': '100',
        'gasUsed': '21000',
        'input': '0x',
        'nonce': '1',
    }
    with patch.object(ethereum_inquirer, 'get_block_by_number', side_effect=AssertionError):
        tx, _ = deserialize_evm_transaction(
            data=tx_data,
            internal=False,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=ethereum_inquirer,
        )

    assert tx.timestamp == expected_timestamp
