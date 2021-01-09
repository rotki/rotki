import os

import pytest

from rotkehlchen.chain.ethereum.manager import (
    ETHEREUM_NODES_TO_CONNECT_AT_START,
    OPEN_NODES,
    OPEN_NODES_WEIGHT_MAP,
    NodeName,
)
from rotkehlchen.constants.ethereum import (
    ATOKEN_ABI,
    ERC20TOKEN_ABI,
    YEARN_YCRV_VAULT,
    ZERO_ADDRESS,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.checks import assert_serialized_dicts_equal
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_TEST_PARAMETERS,
    wait_until_all_nodes_connected,
)


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_block_by_number(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )
    block = ethereum_manager.get_block_by_number(10304885, call_order=call_order)
    assert block['timestamp'] == 1592686213
    assert block['number'] == 10304885
    assert block['hash'] == '0xe2217ba1639c6ca2183f40b0f800185b3901faece2462854b3162d4c5077752c'


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_transaction_receipt(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )
    result = ethereum_manager.get_transaction_receipt(
        '0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89',
        call_order=call_order,
    )
    block_hash = '0x6f3a7838a8788c3371b88df170c3643d19bad896c915a7368681292882b6ad61'

    assert result['blockHash'] == block_hash
    assert len(result['logs']) == 2
    assert result['gasUsed'] == 144046
    assert result['blockNumber'] == 10840714
    assert result['logs'][0]['blockNumber'] == 10840714
    assert result['logs'][1]['blockNumber'] == 10840714
    assert result['status'] == 1
    assert result['transactionIndex'] == 110
    assert result['logs'][0]['transactionIndex'] == 110
    assert result['logs'][1]['transactionIndex'] == 110
    assert result['logs'][0]['logIndex'] == 235
    assert result['logs'][1]['logIndex'] == 236


@pytest.mark.parametrize('ethrpc_endpoint,ethereum_manager_connect_at_start,call_order', [
    (
        '',
        [x for x in OPEN_NODES if x != NodeName.ETHERSCAN],
        [x for x in OPEN_NODES if x != NodeName.ETHERSCAN],
    ),
])
def test_use_open_nodes(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    """Test that we can connect to and use the open nodes (except from etherscan)"""
    # Wait until all nodes are connected
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )
    result = ethereum_manager.get_transaction_receipt(
        '0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89',
        call_order=call_order,
    )
    block_hash = '0x6f3a7838a8788c3371b88df170c3643d19bad896c915a7368681292882b6ad61'
    assert result['blockHash'] == block_hash


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_call_contract(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )

    result = ethereum_manager.call_contract(
        contract_address=YEARN_YCRV_VAULT.address,
        abi=YEARN_YCRV_VAULT.abi,
        method_name='symbol',
        call_order=call_order,
    )
    assert result == 'yyDAI+yUSDC+yUSDT+yTUSD'
    # also test that doing contract.call() has the same result
    result2 = YEARN_YCRV_VAULT.call(ethereum_manager, 'symbol', call_order=call_order)
    assert result == result2
    result = ethereum_manager.call_contract(
        contract_address=YEARN_YCRV_VAULT.address,
        abi=YEARN_YCRV_VAULT.abi,
        method_name='balanceOf',
        arguments=['0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c'],
        call_order=call_order,
    )
    assert result >= 0


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_logs(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )

    argument_filters = {
        'from': '0x7780E86699e941254c8f4D9b7eB08FF7e96BBE10',
        'to': YEARN_YCRV_VAULT.address,
    }
    events = ethereum_manager.get_logs(
        contract_address='0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8',
        abi=ERC20TOKEN_ABI,
        event_name='Transfer',
        argument_filters=argument_filters,
        from_block=10712531,
        to_block=10712753,
        call_order=call_order,
    )
    assert len(events) == 1
    expected_event = {
        'address': '0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8',
        'blockNumber': 10712731,
        'data': '0x0000000000000000000000000000000000000000000001e3f60028423cff0000',
        'gasPrice': 72000000000,
        'gasUsed': 93339,
        'logIndex': 157,
        'topics': [
            '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
            '0x0000000000000000000000007780e86699e941254c8f4d9b7eb08ff7e96bbe10',
            '0x0000000000000000000000005dbcf33d8c2e976c6b560249878e6f1491bca25c',
        ],
        'transactionHash': '0xca33e56e1e529dacc9aa1261c8ba9230927329eb609fbe252e5bd3c2f5f3bcc9',
        'transactionIndex': 85,
    }
    assert_serialized_dicts_equal(
        events[0],
        expected_event,
        same_key_length=False,
        ignore_keys=[
            'timeStamp',  # returned from etherscan
            'blockHash',  # returned from web3
            'removed',  # returned from web3
        ],
    )


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_log_and_receipt_etherscan_bad_tx_index(
        ethereum_manager,
        call_order,
        ethereum_manager_connect_at_start,
):
    """
    https://etherscan.io/tx/0x00eea6359d247c9433d32620358555a0fd3265378ff146b9511b7cff1ecb7829
    contains a log entry which in etherscan has transaction index 0x.

    Our code was not handling this well and was raising ValueError.
    This is a regression test for that.
    """
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )

    # Test getting the offending log entry does not raise
    argument_filters = {
        'from': ZERO_ADDRESS,
        'to': '0xbA215F7BE6c620dA3F8240B82741eaF3C5f5D786',
    }
    events = ethereum_manager.get_logs(
        contract_address='0xFC4B8ED459e00e5400be803A9BB3954234FD50e3',
        abi=ATOKEN_ABI,
        event_name='Transfer',
        argument_filters=argument_filters,
        from_block=10773651,
        to_block=10773653,
        call_order=call_order,
    )
    assert len(events) == 2
    assert events[0]['transactionIndex'] == 0
    assert events[1]['transactionIndex'] == 0

    # Test getting the transaction receipt (also containing the log entries) does not raise
    # They seem to all be 0
    result = ethereum_manager.get_transaction_receipt(
        '0x00eea6359d247c9433d32620358555a0fd3265378ff146b9511b7cff1ecb7829',
        call_order=call_order,
    )
    assert all(x['transactionIndex'] == 0 for x in result['logs'])


def test_nodes_weight_map():
    """Test the weight map has no duplicates and adds to 100%"""
    nodes_set = set()
    total = ZERO
    for node, value in OPEN_NODES_WEIGHT_MAP.items():
        assert node not in nodes_set, f'node {str(node)} appears more than once'
        nodes_set.add(node)
        total += FVal(value)

    assert total == ONE


def test_nodes_sets():
    """Test that all nodes sets contain the nodes they should"""
    assert set(OPEN_NODES) - set({NodeName.ETHERSCAN}) == set(ETHEREUM_NODES_TO_CONNECT_AT_START) - set({NodeName.OWN})  # noqa: E501
    assert set(OPEN_NODES_WEIGHT_MAP.keys()) - set({NodeName.ETHERSCAN}) == set(ETHEREUM_NODES_TO_CONNECT_AT_START) - set({NodeName.OWN})  # noqa: E501


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test is only for us to figure out the speed of the open nodes',
)
def test_nodes_speed():
    """TODO"""


def _test_get_blocknumber_by_time(eth_manager, etherscan):
    result = eth_manager.get_blocknumber_by_time(1577836800, etherscan=etherscan)
    assert result == 9193265


def test_get_blocknumber_by_time_subgraph(ethereum_manager):
    """Queries the blocks subgraph for known block times"""
    _test_get_blocknumber_by_time(ethereum_manager, False)


def test_get_blocknumber_by_time_etherscan(ethereum_manager):
    """Queries etherscan for known block times"""
    _test_get_blocknumber_by_time(ethereum_manager, True)
