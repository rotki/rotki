import os
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import _query_currency_converterapi, _query_exchanges_rateapi
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils import ts_now, tsToDate


@pytest.mark.skipif(
    'TRAVIS' in os.environ,
    reason='some of these APIs frequently become unavailable',
)
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_query_realtime_price_apis(inquirer):
    result = _query_currency_converterapi('USD', 'EUR')
    assert result and isinstance(result, FVal)
    result = _query_exchanges_rateapi('USD', 'GBP')
    assert result and isinstance(result, FVal)
    result = inquirer.query_historical_fiat_exchange_rates('USD', 'CNY', 1411603200)
    assert result == FVal('6.1371932033')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_switching_to_backup_api(inquirer):
    count = 0
    original_get = requests.get

    def mock_exchanges_rateapi_fail(uri):
        nonlocal count
        count += 1
        if 'exchangeratesapi' in uri:
            return MockResponse(501, '{"msg": "some error")')
        return original_get(uri)

    with patch('requests.get', side_effect=mock_exchanges_rateapi_fail):
        result = inquirer.query_fiat_pair('USD', 'EUR')
        assert result and isinstance(result, FVal)
        assert count > 1, 'requests.get should have been called more than once'


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_caching(inquirer):
    def mock_currency_converter_api(uri):
        return MockResponse(200, '{"results": {"USD_EUR": {"val": 1.1543, "id": "USD_EUR"}}}')

    with patch('requests.get', side_effect=mock_currency_converter_api):
        result = inquirer.query_fiat_pair('USD', 'EUR')
        assert result == FVal('1.1543')

    # Now outside the mocked response, we should get same value due to caching
    assert inquirer.query_fiat_pair('USD', 'EUR') == FVal('1.1543')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_fallback_to_cached_values_within_a_month(inquirer):
    def mock_api_remote_fail(uri):
        return MockResponse(500, '{"msg": "shit hit the fan"')

    # Get a date 15 days ago and insert a cached entry for EUR JPY then
    now = ts_now()
    eurjpy_val = FVal('124.123')
    date = tsToDate(now - 86400 * 15, formatstr='%Y-%m-%d')
    inquirer._save_forex_rate(date, 'EUR', 'JPY', eurjpy_val)
    # Get a date 31 days ago and insert a cache entry for EUR CNY then
    date = tsToDate(now - 86400 * 31, formatstr='%Y-%m-%d')
    inquirer._save_forex_rate(date, 'EUR', 'CNY', FVal('7.719'))

    with patch('requests.get', side_effect=mock_api_remote_fail):
        # We fail to find a response but then go back 15 days and find the cached response
        result = inquirer.query_fiat_pair('EUR', 'JPY')
        assert result == eurjpy_val
        # The cached response for EUR CNY is too old so we will fail here
        with pytest.raises(ValueError):
            result = inquirer.query_fiat_pair('EUR', 'CNY')
