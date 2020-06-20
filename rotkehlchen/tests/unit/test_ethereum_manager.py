import pytest

from rotkehlchen.tests.utils.ethereum import ETHEREUM_TEST_PARAMETERS


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_block_by_number(ethereum_manager):
    block = ethereum_manager.get_block_by_number(10304885)
    assert block['timestamp'] == 1592686213
    assert block['number'] == 10304885
    assert block['hash'] == '0xe2217ba1639c6ca2183f40b0f800185b3901faece2462854b3162d4c5077752c'
