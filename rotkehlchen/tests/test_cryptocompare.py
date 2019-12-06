import os
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.errors import NoPriceForGivenTimestamp
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_SNGLS


def test_cryptocompare_query_pricehistorical(accounting_data_dir):
    """Test that cryptocompare price historical query works fine"""
    cc = Cryptocompare(data_directory=accounting_data_dir)
    price = cc.query_endpoint_pricehistorical(
        from_asset=A_SNGLS,
        to_asset=A_BTC,
        timestamp=1475413990,
    )
    # Just test a price is returned
    assert price


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_historical_data_use_cached_price(accounting_data_dir):
    """Test that the cryptocompare cache is used and also properly deserialized"""
    # Create a cache file for SNGSL_BTC
    contents = """{"start_time": 0, "end_time": 1439390800,
    "data": [{"time": 1438387200, "close": 10, "high": 10, "low": 10, "open": 10,
    "volumefrom": 10, "volumeto": 10}, {"time": 1438390800, "close": 20, "high": 20,
    "low": 20, "open": 20, "volumefrom": 20, "volumeto": 20}]}"""
    with open(os.path.join(accounting_data_dir, 'price_history_SNGLS_BTC.json'), 'w') as f:
        f.write(contents)

    cc = Cryptocompare(data_directory=accounting_data_dir)
    with patch.object(cc, 'query_endpoint_histohour') as histohour_mock:
        result = cc.get_historical_data(
            from_asset=A_SNGLS,
            to_asset=A_BTC,
            timestamp=1438390801,
            historical_data_start=0,
        )
        # make sure that histohour was not called, in essence that the cache was used
        assert histohour_mock.call_count == 0

    assert len(result) == 2
    assert isinstance(result[0].low, FVal)
    assert result[0].low == FVal(10)
    assert isinstance(result[0].high, FVal)
    assert result[0].high == FVal(10)
    assert isinstance(result[1].low, FVal)
    assert result[1].low == FVal(20)
    assert isinstance(result[1].high, FVal)
    assert result[1].high == FVal(20)


@pytest.mark.skip(
    'Same test as test_end_to_end_tax_report::'
    'test_cryptocompare_asset_and_price_not_found_in_history_processing',
)
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_cryptocompare_histohour_query_old_ts_xcp(
        accounting_data_dir,
        price_historian,  # pylint: disable=unused-argument
):
    """Test that as a result of this query a crash does not happen.

    Regression for: https://github.com/rotki/rotki/issues/432
    Unfortunately still no price is found so we have to expect a NoPriceForGivenTimestamp

    This test is now skipped since it's a subset of:
    test_end_to_end_tax_report::test_cryptocompare_asset_and_price_not_found_in_history_processing

    When more price data sources are introduced then this should probably be unskipped
    to focus on the cryptocompare case. But at the moment both tests follow the same
    path and are probably slow due to the price querying.
    """
    with pytest.raises(NoPriceForGivenTimestamp):
        cc = Cryptocompare(data_directory=accounting_data_dir)
        cc.query_historical_price(
            from_asset=Asset('XCP'),
            to_asset=A_USD,
            timestamp=1392685761,
            historical_data_start=1438387200,
        )


def test_cryptocompare_dao_query(accounting_data_dir):
    """
    Test that querying the DAO token for cryptocompare historical prices works. At some point
    it got accidentaly removed from cryptocompare. Then it got fixed.
    This test will show us if this happens again.

    Regression test for https://github.com/rotki/rotki/issues/548
    """
    cc = Cryptocompare(data_directory=accounting_data_dir)
    price = cc.query_historical_price(
        from_asset=Asset('DAO'),
        to_asset=A_USD,
        timestamp=1468886400,
        historical_data_start=1438387200,
    )
    assert price is not None
