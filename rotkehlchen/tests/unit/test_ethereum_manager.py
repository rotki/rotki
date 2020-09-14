import pytest

from rotkehlchen.tests.utils.ethereum import ETHEREUM_TEST_PARAMETERS


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_block_by_number(ethereum_manager):
    block = ethereum_manager.get_block_by_number(10304885)
    assert block['timestamp'] == 1592686213
    assert block['number'] == 10304885
    assert block['hash'] == '0xe2217ba1639c6ca2183f40b0f800185b3901faece2462854b3162d4c5077752c'


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_transaction_receipt(ethereum_manager):
    result = ethereum_manager.get_transaction_receipt(
        '0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89',
    )
    block_hash = '0x6f3a7838a8788c3371b88df170c3643d19bad896c915a7368681292882b6ad61'
    assert result['blockHash'] == block_hash
    assert len(result['logs']) == 2
    assert result['gasUsed'] == '0x232ae'
