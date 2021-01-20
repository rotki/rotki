import random
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)


@pytest.mark.parametrize('assets, error_message', [
    ('', 'Not a valid list'),
    ([], 'Shorter than minimum length 1'),
    (['unknown_asset'], 'Unknown asset unknown_asset'),
])
def test_get_current_assets_price_validation_error(
        rotkehlchen_api_server,
        assets,
        error_message,
):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "currentassetspriceresource",
        ),
        json={'assets': assets},
    )
    assert_error_response(
        response=response,
        contained_in_msg=error_message,
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_get_current_assets_price(rotkehlchen_api_server):

    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "currentassetspriceresource",
        ),
        json={
            'assets': ['BTC', 'USD'],
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 2
    assert result['BTC'] == '1.5'
    assert result['USD'] == '1.5'
