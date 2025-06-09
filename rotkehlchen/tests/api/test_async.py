from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.exchanges import mock_binance_balance_response, try_get_first_exchange
from rotkehlchen.types import Location
from rotkehlchen.utils.gevent_compat import sleep

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_query_async_tasks(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
    """Test that querying the outcomes of async tasks works as expected

    We don't mock price queries in this test only because that cause the tasks
    list test below to fail since due to the mocking the tasks returns immediately and
    does not wait on a gevent context switching. So if we mock we don't get to
    test the task is still pending functionality.
    """

    # async query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = try_get_first_exchange(server.rest_api.rotkehlchen.exchange_manager, Location.BINANCE)  # noqa: E501
    assert binance is not None
    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_balance_response)

    # Check querying the async task resource when no async task is scheduled
    response = requests.get(api_url_for(server, 'asynctasksresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result == {'completed': [], 'pending': []}

    # Create an async task
    with binance_patch:
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'async_query': True})
        task_id = assert_ok_async_response(response)

        # now check that there is a task
        response = requests.get(api_url_for(server, 'asynctasksresource'))
        result = assert_proper_sync_response_with_result(response)
        assert result == {'completed': [], 'pending': [task_id]}

        # now query for the task result and see it's still pending (test for task lists)
        response = requests.get(
            api_url_for(server, 'specific_async_tasks_resource', task_id=task_id),
        )
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == 'The task with id 0 is still pending'
        assert json_data['result'] == {'status': 'pending', 'outcome': None}

        while True:
            # and now query for the task result and assert on it
            response = requests.get(
                api_url_for(server, 'specific_async_tasks_resource', task_id=task_id),
            )
            assert_proper_response(response)
            json_data = response.json()
            if json_data['result']['status'] == 'pending':
                # context switch so that the greenlet to query balances can operate
                sleep(1)
            elif json_data['result']['status'] == 'completed':
                break
            else:
                raise AssertionError(f"Unexpected status: {json_data['result']['status']}")

    assert json_data['message'] == ''
    assert json_data['result']['status'] == 'completed'
    # assert that there is an outcome
    assert json_data['result']['outcome'] is not None
    assert json_data['result']['outcome']['result'] is not None
    assert json_data['result']['outcome']['message'] == ''

    # Finally try to query an unknown task id and check proper error is returned
    response = requests.get(
        api_url_for(server, 'specific_async_tasks_resource', task_id=568),
    )
    assert_error_response(
        response=response,
        contained_in_msg='No task with id 568 found',
        status_code=HTTPStatus.NOT_FOUND,
        result_exists=True,
    )
    json_data = response.json()
    assert json_data['result'] == {'status': 'not-found', 'outcome': None}


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE,)])
def test_query_async_task_that_died(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
    """If an async task dies with an exception check that it's properly handled"""

    # async query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = try_get_first_exchange(server.rest_api.rotkehlchen.exchange_manager, Location.BINANCE)  # noqa: E501
    assert binance is not None

    def mock_binance_asset_return(*args: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        raise ValueError('BOOM!')

    binance_patch = patch.object(binance.session, 'request', side_effect=mock_binance_asset_return)

    # Create an async task
    with binance_patch:
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    # now check that there is a task
    response = requests.get(api_url_for(server, 'asynctasksresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result == {'completed': [task_id], 'pending': []}

    while True:
        # and now query for the task result and assert on it
        response = requests.get(
            api_url_for(server, 'specific_async_tasks_resource', task_id=task_id),
        )
        result = assert_proper_sync_response_with_result(response)
        if result['status'] == 'pending':
            # context switch so that the greenlet to query balances can operate
            sleep(1)
        elif result['status'] == 'completed':
            break
        else:
            raise AssertionError(f"Unexpected status: {result['status']}")

    assert result['status'] == 'completed'
    # assert that the backend task query died and we detect it
    assert result['outcome'] is not None
    assert result['outcome']['result'] is None
    msg = 'The backend query task died unexpectedly: BOOM!'
    assert result['outcome']['message'] == msg


def test_cancel_async_task(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
    """Test that canceling an ongoing async task works fine"""
    # async query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = try_get_first_exchange(server.rest_api.rotkehlchen.exchange_manager, Location.BINANCE)  # noqa: E501
    assert binance is not None

    def mock_binance_asset_return(*args: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        while True:  # infinite loop so we can cancel it
            sleep(1)

    binance_patch = patch.object(binance.session, 'request', side_effect=mock_binance_asset_return)

    # Create an async task
    with binance_patch:
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    # now check that there is a task
    response = requests.get(api_url_for(server, 'asynctasksresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result == {'completed': [], 'pending': [task_id]}

    response = requests.delete(api_url_for(server, 'specific_async_tasks_resource', task_id=666))
    assert_error_response(
        response=response,
        contained_in_msg='Did not cancel task with id 666',
        status_code=HTTPStatus.NOT_FOUND,
    )
    response = requests.delete(api_url_for(server, 'specific_async_tasks_resource', task_id=task_id))  # noqa: E501
    assert_simple_ok_response(response)

    # now check that there is no task left
    response = requests.get(api_url_for(server, 'asynctasksresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result == {'completed': [], 'pending': []}
