import random
from datetime import datetime
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)


@pytest.mark.freeze_time(datetime(2021, 1, 21, 11, 36, 15))
@pytest.mark.parametrize('assets_timestamp, error_message', [
    ('', 'Not a valid list'),
    ([], 'Shorter than minimum length 1'),
    ([[]], 'Length must be 2'),
    ([['BTC']], 'Length must be 2'),
    ([['unknown_asset', 1611166335]], 'Unknown asset unknown_asset'),
    ([['BTC', 9999999999999]], 'year 318857 is out of range'),
    ([['BTC', 1611166335, 'BTC']], 'Length must be 2'),
    ([['BTC', 1611166335], []], 'Length must be 2'),
    ([['BTC', 1611187201]], 'Timestamps must be equal or less than 1611187200'),
])
def test_get_historical_assets_price_invalid_json(
        rotkehlchen_api_server,
        assets_timestamp,
        error_message,
):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={'assets_timestamp': assets_timestamp},
    )
    assert_error_response(
        response=response,
        contained_in_msg=error_message,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('mocked_price_queries', [{
    'BTC': {'USD': {1611166335: FVal('30000')}},
    'USD': {'USD': {1579543935: FVal('1')}},
    'GBP': {'USD': {1548007935: FVal('1.25')}},
    'ETH': {'USD': {
        1611166335: FVal('0'),
        1589716063: FVal('1'),
    }},
}])
def test_get_historical_assets_price(rotkehlchen_api_server):
    """Test given a list of asset-timestamp tuples it returns the asset price
    at the given timestamp.

    NB: the current implementation only returns one price per asset. Requesting
    multiple timestamps for the same asset will return the price of the last
    timestamp in the request body (i.e. ETH at 1589716063).
    """
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'assets_timestamp': [
                ['ETH', 1611166335],
                ['BTC', 1611166335],
                ['USD', 1579543935],
                ['GBP', 1548007935],
                ['ETH', 1589716063],
            ],
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 4
    assert result['BTC'] == {
        'timestamp': 1611166335,
        'usd_price': '30000',
    }
    assert result['USD'] == {
        'timestamp': 1579543935,
        'usd_price': '1',
    }
    assert result['GBP'] == {
        'timestamp': 1548007935,
        'usd_price': '1.25',
    }
    assert result['ETH'] == {
        'timestamp': 1589716063,
        'usd_price': '1',
    }
