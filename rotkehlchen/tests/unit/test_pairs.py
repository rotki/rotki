import pytest

from rotkehlchen.constants.assets import A_BTC, A_EUR
from rotkehlchen.errors.asset import UnprocessableTradePair
from rotkehlchen.exchanges.data_structures import trade_pair_from_assets
from rotkehlchen.serialization.deserialize import get_pair_position_str
from rotkehlchen.types import TradePair


def test_trade_pair_from_assets():
    pair = trade_pair_from_assets(A_BTC, A_EUR)
    assert pair == TradePair('BTC_EUR')


def test_get_pair_position_str():
    assert get_pair_position_str('ETH_BTC', 'first') == 'ETH'
    assert get_pair_position_str('ETH_BTC', 'second') == 'BTC'

    with pytest.raises(AssertionError):
        get_pair_position_str('ETH_BTC', 'third')
    with pytest.raises(AssertionError):
        get_pair_position_str('ETH_BTC', 'sdsadsad')

    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str('_', 'first')
    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str('ETH_', 'first')
    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str('_BTC', 'second')
    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str('ETH_BTC_USD', 'first')

    # This function does not checks for known assets
    assert get_pair_position_str('ETH_FDFSFDSFDSF', 'first') == 'ETH'
    assert get_pair_position_str('FDFSFDSFDSF_BTC', 'first') == 'FDFSFDSFDSF'

    assert get_pair_position_str('ETH_RDN', 'first') == 'ETH'
    assert get_pair_position_str('ETH_RDN', 'second') == 'RDN'
