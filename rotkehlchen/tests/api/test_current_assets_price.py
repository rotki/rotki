import random

import pytest
import requests

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)


@pytest.mark.parametrize('mocked_current_prices', [{
    ('BTC', 'USD'): FVal('33183.98'),
    ('GBP', 'USD'): FVal('1.367'),
}])
def test_get_current_assets_price_in_usd(rotkehlchen_api_server):
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "currentassetspriceresource",
        ),
        json={
            'assets': ['BTC', 'USD', 'GBP'],
            'target_asset': 'USD',
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 2
    assert result['assets']['BTC'] == '33183.98'
    assert result['assets']['GBP'] == '1.367'
    assert result['assets']['USD'] == '1'
    assert result['target_asset'] == 'USD'


@pytest.mark.parametrize('mocked_current_prices', [{
    ('USD', 'BTC'): FVal('0.00003013502298398202988309419184'),
    ('GBP', 'BTC'): FVal('0.00004119457641910343485018976024'),
}])
def test_get_current_assets_price_in_btc(rotkehlchen_api_server):

    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "currentassetspriceresource",
        ),
        json={
            'assets': ['BTC', 'USD', 'GBP'],
            'target_asset': 'BTC',
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 2
    assert result['assets']['BTC'] == '1'
    assert result['assets']['GBP'] == '0.00004119457641910343485018976024'
    assert result['assets']['USD'] == '0.00003013502298398202988309419184'
    assert result['target_asset'] == 'BTC'
