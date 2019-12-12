from http import HTTPStatus
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
)
from rotkehlchen.tests.utils.exchanges import BINANCE_BALANCES_RESPONSE
from rotkehlchen.tests.utils.mock import MockResponse


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_async_tasks(rotkehlchen_api_server_with_exchanges):
    """Test that querying the outcomes of async tasks works as expected"""

    # async query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['binance']

    def mock_binance_asset_return(url):  # pylint: disable=unused-argument
        return MockResponse(200, BINANCE_BALANCES_RESPONSE)

    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_asset_return)

    # Check querying the async taks resource when no async task is scheduled
    response = requests.get(api_url_for(server, "asynctasksresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == []

    # Create an async task
    with binance_patch:
        response = requests.get(api_url_for(
            server,
            "named_exchanges_balances_resource",
            name='binance',
        ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    # now check that there is a task
    response = requests.get(api_url_for(server, "asynctasksresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == [task_id]

    # now query for the task result and see it's still pending (test for task lists)
    response = requests.get(
        api_url_for(server, "specific_async_tasks_resource", task_id=task_id),
    )
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == 'The task with id 0 is still pending'
    assert json_data['result'] == {'status': 'pending', 'outcome': None}

    while True:
        # and now query for the task result and assert on it
        response = requests.get(
            api_url_for(server, "specific_async_tasks_resource", task_id=task_id),
        )
        assert_proper_response(response)
        json_data = response.json()
        if json_data['result']['status'] == 'pending':
            # context switch so that the greenlet to query balances can operate
            gevent.sleep(1)
        elif json_data['result']['status'] == 'completed':
            break
        else:
            raise AssertionError(f"Unexpected status: {json_data['result']['status']}")

    assert json_data['message'] == ''
    assert json_data['result']['status'] == 'completed'
    # assert that there is an outcome
    assert json_data['result']['outcome'] is not None
    assert json_data['result']['outcome']['result'] is not None

    # Finally try to query an unknown task id and check proper error is returned
    response = requests.get(
        api_url_for(server, "specific_async_tasks_resource", task_id=568),
    )
    assert_error_response(
        response=response,
        contained_in_msg='No task with id 568 found',
        status_code=HTTPStatus.NOT_FOUND,
    )
    json_data = response.json()
    assert json_data['result'] == {'status': 'not-found', 'outcome': None}
