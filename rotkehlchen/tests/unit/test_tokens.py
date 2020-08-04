import pytest

from rotkehlchen.chain.ethereum.tokens import EthTokens
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal


@pytest.fixture
def ethtokens(ethereum_manager, database):
    return EthTokens(database, ethereum_manager)


def test_detect_tokens_for_addresses(ethtokens, inquirer):  # pylint: disable=unused-argument
    """
    Autodetect tokens of two addresses

    This is going to be a bit slow test since it actually queries etherscan without any mocks.
    By doing so we can test that the whole behaviou with etherscan works fine and our
    chosen chunk length for it is also acceptable.

    USD price queries are mocked so we don't care about the result.
    Just check that all prices are included
    """
    addr1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    addr2 = '0xD3A962916a19146D658de0ab62ee237ed3115873'
    result, token_usd_prices = ethtokens.detect_tokens_for_addresses([addr1, addr2])

    assert len(result[addr1]) >= 2
    balance = result[addr1]['aDAI']
    assert isinstance(balance, FVal)
    assert balance > ZERO
    assert len(result[addr2]) >= 20

    assert len(token_usd_prices) == len(set(result[addr1].keys()).union(set(result[addr2].keys())))
