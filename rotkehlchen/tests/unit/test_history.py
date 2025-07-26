import pytest

from rotkehlchen.history.types import HistoricalPriceOracle


@pytest.mark.parametrize(('value', 'result'), [
    ('manual', HistoricalPriceOracle.MANUAL),
    ('coingecko', HistoricalPriceOracle.COINGECKO),
    ('cryptocompare', HistoricalPriceOracle.CRYPTOCOMPARE),
    ('xratescom', HistoricalPriceOracle.XRATESCOM),
])
def test_historical_price_oracle_deserialize(value, result):
    assert HistoricalPriceOracle.deserialize(value) == result
