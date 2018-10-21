import pytest

from rotkehlchen.kraken import (
    KRAKEN_ASSETS,
    WORLD_TO_KRAKEN,
    kraken_to_world_pair,
    trade_from_kraken,
)
from rotkehlchen.order_formatting import Trade
from rotkehlchen.utils import ts_now


def test_coverage_of_kraken_balances(kraken):
    all_assets = set(kraken.query_public('Assets').keys())
    diff = set(KRAKEN_ASSETS).symmetric_difference(all_assets)
    assert len(diff) == 0, (
        f"Our known assets don't match kraken's assets. Difference: {diff}"
    )


def test_querying_balances(kraken):
    result, error_or_empty = kraken.query_balances()
    assert error_or_empty == ''
    assert isinstance(result, dict)
    for name, entry in result.items():
        assert name in WORLD_TO_KRAKEN
        assert 'usd_value' in entry
        assert 'amount' in entry


def test_querying_trade_history(kraken):
    now = ts_now()
    result = kraken.query_trade_history(
        start_ts=1451606400,
        end_ts=now,
        end_at_least_ts=now,
    )
    assert isinstance(result, list)
    assert len(result) != 0

    for kraken_trade in result:
        trade = trade_from_kraken(kraken_trade)
        assert isinstance(trade, Trade)


def test_querying_deposits_withdrawals(kraken):
    now = ts_now()
    result = kraken.query_trade_history(
        start_ts=1451606400,
        end_ts=now,
        end_at_least_ts=now,
    )
    assert isinstance(result, list)
    assert len(result) != 0


def test_kraken_to_world_pair():
    assert kraken_to_world_pair('QTUMXBT') == 'QTUM_BTC'
    assert kraken_to_world_pair('ADACAD') == 'ADA_CAD'
    assert kraken_to_world_pair('BCHUSD') == 'BCH_USD'
    assert kraken_to_world_pair('DASHUSD') == 'DASH_USD'
    assert kraken_to_world_pair('XTZETH') == 'XTZ_ETH'
    assert kraken_to_world_pair('XXBTZGBP.d') == 'BTC_GBP'

    with pytest.raises(ValueError):
        kraken_to_world_pair('GABOOBABOO')
