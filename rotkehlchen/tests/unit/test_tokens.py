import pytest

from rotkehlchen.chain.ethereum.tokens import EthTokens
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal


@pytest.fixture
def ethtokens(ethereum_manager, database):
    return EthTokens(database, ethereum_manager)


def test_detect_tokens_for_addresses(ethtokens):
    result = ethtokens.detect_tokens_for_addresses(
        ['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
         '0xD3A962916a19146D658de0ab62ee237ed3115873'])

    assert len(result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']) >= 2
    balance = result['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']['aDAI']
    assert isinstance(balance, FVal)
    assert balance > ZERO
    assert len(result['0xD3A962916a19146D658de0ab62ee237ed3115873']) >= 20
