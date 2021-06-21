import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.errors import UnknownAsset, UnprocessableTradePair
from rotkehlchen.exchanges.data_structures import trade_pair_from_assets
from rotkehlchen.serialization.deserialize import get_pair_position_str, pair_get_assets
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.typing import TradePair


def test_trade_pair_from_assets():
    pair = trade_pair_from_assets(A_BTC, A_EUR)
    assert pair == TradePair('BTC_EUR')


def test_pair_get_assets():
    a1, a2 = pair_get_assets('ETH_BTC')
    assert isinstance(a1, Asset)
    assert a1 == A_ETH
    assert isinstance(a2, Asset)
    assert a2 == A_BTC

    with pytest.raises(UnprocessableTradePair):
        pair_get_assets('_')
    with pytest.raises(UnprocessableTradePair):
        pair_get_assets('ETH_')
    with pytest.raises(UnprocessableTradePair):
        pair_get_assets('_BTC')
    with pytest.raises(UnprocessableTradePair):
        pair_get_assets('ETH_BTC_USD')

    with pytest.raises(UnknownAsset):
        pair_get_assets('ETH_FDFSFDSFDSF')
    with pytest.raises(UnknownAsset):
        pair_get_assets('FDFSFDSFDSF_BTC')

    a1, a2 = pair_get_assets('ETH_RDN')
    assert isinstance(a1, Asset)
    assert a1 == A_ETH
    assert isinstance(a2, Asset)
    assert a2 == A_RDN


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
