import gevent
import pytest

from rotkehlchen.chain.ethereum.manager import NodeName
from rotkehlchen.tests.utils.ethereum import ETHEREUM_TEST_PARAMETERS


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_block_by_number(ethereum_manager, call_order):
    # Wait until all nodes are connected
    if NodeName.OWN in call_order:
        while NodeName.OWN not in ethereum_manager.web3_mapping:
            gevent.sleep(2)
            continue
    block = ethereum_manager.get_block_by_number(10304885, call_order=call_order)
    assert block['timestamp'] == 1592686213
    assert block['number'] == 10304885
    assert block['hash'] == '0xe2217ba1639c6ca2183f40b0f800185b3901faece2462854b3162d4c5077752c'


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_transaction_receipt(ethereum_manager, call_order):
    # Wait until all nodes are connected
    if NodeName.OWN in call_order:
        while NodeName.OWN not in ethereum_manager.web3_mapping:
            gevent.sleep(2)
            continue
    result = ethereum_manager.get_transaction_receipt(
        '0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89',
        call_order=call_order
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
        (NodeName.MYCRYPTO, NodeName.AVADO_POOL, NodeName.BLOCKSCOUT),
        (NodeName.MYCRYPTO, NodeName.AVADO_POOL, NodeName.BLOCKSCOUT),
    ),
])
def test_use_open_nodes(ethereum_manager, call_order):
    """Test that we can connect to and use the open nodes (except from etherscan)"""
    # Wait until all nodes are connected
    while len(ethereum_manager.web3_mapping) < 3:
        gevent.sleep(2)
        continue
    result = ethereum_manager.get_transaction_receipt(
        '0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89',
        call_order=call_order
    )
    block_hash = '0x6f3a7838a8788c3371b88df170c3643d19bad896c915a7368681292882b6ad61'
    assert result['blockHash'] == block_hash
