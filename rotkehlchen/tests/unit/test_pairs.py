import pytest

from rotkehlchen.errors.asset import UnprocessableTradePair
from rotkehlchen.serialization.deserialize import get_pair_position_str
from rotkehlchen.types import TradePair


def test_get_pair_position_str() -> None:
    assert get_pair_position_str(TradePair('ETH_BTC'), 'first') == 'ETH'
    assert get_pair_position_str(TradePair('ETH_BTC'), 'second') == 'BTC'

    with pytest.raises(AssertionError):
        get_pair_position_str(TradePair('ETH_BTC'), 'third')
    with pytest.raises(AssertionError):
        get_pair_position_str(TradePair('ETH_BTC'), 'sdsadsad')

    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str(TradePair('_'), 'first')
    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str(TradePair('ETH_'), 'first')
    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str(TradePair('_BTC'), 'second')
    with pytest.raises(UnprocessableTradePair):
        get_pair_position_str(TradePair('ETH_BTC_USD'), 'first')

    # This function does not checks for known assets
    assert get_pair_position_str(TradePair('ETH_FDFSFDSFDSF'), 'first') == 'ETH'
    assert get_pair_position_str(TradePair('FDFSFDSFDSF_BTC'), 'first') == 'FDFSFDSFDSF'

    assert get_pair_position_str(TradePair('ETH_RDN'), 'first') == 'ETH'
    assert get_pair_position_str(TradePair('ETH_RDN'), 'second') == 'RDN'
