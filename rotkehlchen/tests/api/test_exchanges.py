from http import HTTPStatus
from typing import Any, Dict, List
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.exchanges import (
    BINANCE_BALANCES_RESPONSE,
    BINANCE_MYTRADES_RESPONSE,
    POLONIEX_BALANCES_RESPONSE,
    POLONIEX_TRADES_RESPONSE,
)
from rotkehlchen.tests.utils.mock import MockResponse

API_KEYPAIR_VALIDATION_PATCH = patch(
    'rotkehlchen.exchanges.kraken.Kraken.validate_api_key',
    return_value=(True, ''),
)


def test_setup_exchange(rotkehlchen_api_server):
    """Test that setting up an exchange via the api works"""
    # Check that no exchanges are registered
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == []

    # First test that if api key validation fails we get an error
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    response = requests.put(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Provided API Key or secret is in invalid Format',
        status_code=HTTPStatus.CONFLICT,
    )

    # Mock the api pair validation and make sure that the exchange is setup
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_simple_ok_response(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == ['kraken']

    # Check that we get an error if we try to re-setup an already setup exchange
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Exchange kraken is already registered',
        status_code=HTTPStatus.CONFLICT,
    )


def test_setup_exchange_errors(rotkehlchen_api_server):
    """Test errors and edge cases of setup_exchange endpoint"""

    # Provide unsupported exchange name
    data = {'name': 'superexchange', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Exchange superexchange is not supported',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type exchange name
    data = {'name': 3434, 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Exchange name should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit exchange name
    data = {'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for api key
    data = {'name': 'kraken', 'api_key': True, 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api key
    data = {'name': 'kraken', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for api secret
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 234.1}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api secret
    data = {'name': 'kraken', 'api_key': 'ddddd'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_remove_exchange(rotkehlchen_api_server):
    """Test that removing a setup exchange via the api works"""
    # Setup kraken exchange
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_simple_ok_response(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == ['kraken']

    # Now remove the registered kraken exchange
    data = {'name': 'kraken'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_simple_ok_response(response)
    # and check that it's not registered anymore
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == []

    # now try to remove a non-registered exchange
    data = {'name': 'binance'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Exchange binance is not registered',
        status_code=HTTPStatus.CONFLICT,
    )


def test_remove_exchange_errors(rotkehlchen_api_server):
    """Errors and edge cases when using the remove exchange endpoint"""
    # remove unsupported exchange
    data = {'name': 'wowexchange'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Exchange wowexchange is not supported',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for exchange name
    data = {'name': 5533}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Exchange name should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # omit exchange name at removal
    data = {'name': 5533}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def assert_binance_balances_result(balances: Dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '4723846.89208129'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '4763368.68006011'
    assert balances['ETH']['usd_value'] is not None


def assert_poloniex_balances_result(balances: Dict[str, Any]) -> None:
    assert balances['BTC']['amount'] == '5.5'
    assert balances['BTC']['usd_value'] is not None
    assert balances['ETH']['amount'] == '11.0'
    assert balances['ETH']['usd_value'] is not None


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_balances(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange balances query endpoint works fine"""

    # query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['binance']

    def mock_binance_asset_return(url):  # pylint: disable=unused-argument
        return MockResponse(200, BINANCE_BALANCES_RESPONSE)

    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_asset_return)

    with binance_patch:
        response = requests.get(api_url_for(
            server,
            "named_exchanges_balances_resource",
            name='binance',
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert_binance_balances_result(json_data['result'])

    # query balances of all setup exchanges
    poloniex = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['poloniex']

    def mock_poloniex_asset_return(url, req):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_BALANCES_RESPONSE)

    poloniex_patch = patch.object(poloniex.session, 'post', side_effect=mock_poloniex_asset_return)

    with binance_patch, poloniex_patch:
        response = requests.get(api_url_for(server, "exchangebalancesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert_binance_balances_result(result['binance'])
    assert_poloniex_balances_result(result['poloniex'])


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_balances_async(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange balances query endpoint works fine for async calls"""

    # async query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['binance']

    def mock_binance_asset_return(url):  # pylint: disable=unused-argument
        return MockResponse(200, BINANCE_BALANCES_RESPONSE)

    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_asset_return)

    with binance_patch:
        response = requests.get(api_url_for(
            server,
            "named_exchanges_balances_resource",
            name='binance',
        ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    # now check that there is a task (this is also a test for task list getting)
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

    # context switch so that the greenlet to query balances can operate
    gevent.sleep(.8)

    # and now query for the task result and assert on it
    response = requests.get(
        api_url_for(server, "specific_async_tasks_resource", task_id=task_id),
    )
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result']['status'] == 'completed'
    assert_binance_balances_result(json_data['result']['outcome']['result'])

    # async query balances of all setup exchanges
    poloniex = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['poloniex']

    def mock_poloniex_asset_return(url, req):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_BALANCES_RESPONSE)

    poloniex_patch = patch.object(poloniex.session, 'post', side_effect=mock_poloniex_asset_return)

    with binance_patch, poloniex_patch:
        response = requests.get(
            api_url_for(server, "exchangebalancesresource"),
            json={'async_query': True},
        )
    task_id = assert_ok_async_response(response)

    # context switch so that the greenlet to query balances can operate
    gevent.sleep(.8)

    # and now query for the task result and assert on it
    response = requests.get(
        api_url_for(server, "specific_async_tasks_resource", task_id=task_id),
    )
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result']['status'] == 'completed'
    result = json_data['result']['outcome']['result']
    assert_binance_balances_result(result['binance'])
    assert_poloniex_balances_result(result['poloniex'])


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_balances_errors(rotkehlchen_api_server_with_exchanges):
    """Test errors and edge cases of the exchange balances query endpoint"""
    server = rotkehlchen_api_server_with_exchanges
    # Invalid exchange
    response = requests.get(api_url_for(
        server,
        "named_exchanges_balances_resource",
        name='dasdsad',
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Exchange dasdsad is not supported',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # not registered exchange
    response = requests.get(api_url_for(
        server,
        "named_exchanges_balances_resource",
        name='kraken',
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Could not query balances for kraken since it is not registered',
        status_code=HTTPStatus.CONFLICT,
    )


def assert_binance_trades_result(trades: List[Dict[str, Any]]) -> None:
    assert len(trades) == 1
    trade = trades[0]
    assert trade['timestamp'] == 1499865549
    assert trade['location'] == 'binance'
    assert trade['pair'] == 'BNB_BTC'
    assert trade['trade_type'] == 'buy'
    assert trade['amount'] == '12.0'
    assert trade['rate'] == '4.000001'
    assert trade['fee'] == '10.1'
    assert trade['fee_currency'] == 'BNB'
    assert trade['link'] == '28457'
    assert trade['notes'] == ''


def assert_poloniex_trades_result(trades: List[Dict[str, Any]]) -> None:
    """Poloniex result has two trades but we query with a limited to_ts here so we only get one"""
    assert len(trades) == 1
    trade = trades[0]
    assert trade['timestamp'] == 1539709423
    assert trade['location'] == 'poloniex'
    assert trade['pair'] == 'ETH_BTC'
    assert trade['trade_type'] == 'buy'
    assert trade['amount'] == '3600.53748129'
    assert trade['rate'] == '0.00003432'
    assert trade['fee'] == '7.20107496258'
    assert trade['fee_currency'] == 'ETH'
    assert trade['link'] == '394127361'
    assert trade['notes'] == ''


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_trades(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange trades query endpoint works fine"""
    server = rotkehlchen_api_server_with_exchanges
    # query trades of one specific exchange
    binance = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['binance']

    def mock_binance_trades_return(url):  # pylint: disable=unused-argument
        text = '[]'
        if 'symbol=BNBBTC' in url or 'symbol=BTCBBTC' in url:
            text = BINANCE_MYTRADES_RESPONSE
        return MockResponse(200, text)

    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_trades_return)

    with binance_patch:
        response = requests.get(api_url_for(
            server,
            "named_exchanges_trades_resource",
            name='binance',
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_binance_trades_result(json_data['result'])

    # query trades of all exchanges and in a specific range
    poloniex = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['poloniex']

    def mock_polo_trades_return(url, req):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_TRADES_RESPONSE)

    poloniex_patch = patch.object(poloniex.session, 'post', side_effect=mock_polo_trades_return)

    data = {'from_timestamp': 1499865548, 'to_timestamp': 1539709433}
    with binance_patch, poloniex_patch:
        response = requests.get(api_url_for(server, "exchangetradesresource"), json=data)
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert len(json_data['result']) == 2, 'only two exchanges should be registered'
    assert_binance_trades_result(json_data['result']['binance'])
    assert_poloniex_trades_result(json_data['result']['poloniex'])


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_trades_async(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange trades query endpoint works fine when called asynchronously"""
    server = rotkehlchen_api_server_with_exchanges
    # async query trades of one specific exchange
    binance = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['binance']

    def mock_binance_trades_return(url):  # pylint: disable=unused-argument
        text = '[]'
        if 'symbol=BNBBTC' in url or 'symbol=BTCBBTC' in url:
            text = BINANCE_MYTRADES_RESPONSE
        return MockResponse(200, text)

    binance_patch = patch.object(binance.session, 'get', side_effect=mock_binance_trades_return)

    with binance_patch:
        response = requests.get(api_url_for(
            server,
            "named_exchanges_trades_resource",
            name='binance',
        ), json={'async_query': True})
    task_id = assert_ok_async_response(response)

    # context switch so that the greenlet to query trades can operate
    gevent.sleep(.8)

    # and now query for the task result and assert on it
    response = requests.get(
        api_url_for(server, "specific_async_tasks_resource", task_id=task_id),
    )
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result']['status'] == 'completed'
    assert_binance_trades_result(json_data['result']['outcome']['result'])

    # query trades of all exchanges and in a specific range asynchronously
    poloniex = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['poloniex']

    def mock_polo_trades_return(url, req):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_TRADES_RESPONSE)

    poloniex_patch = patch.object(poloniex.session, 'post', side_effect=mock_polo_trades_return)

    data = {'from_timestamp': 1499865548, 'to_timestamp': 1539709433, 'async_query': True}
    with binance_patch, poloniex_patch:
        response = requests.get(api_url_for(server, "exchangetradesresource"), json=data)
    task_id = assert_ok_async_response(response)

    # context switch so that the greenlet to query trades can operate
    gevent.sleep(.8)

    # and now query for the task result and assert on it
    response = requests.get(
        api_url_for(server, "specific_async_tasks_resource", task_id=task_id),
    )
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result']['status'] == 'completed'
    result = json_data['result']['outcome']['result']
    assert_binance_trades_result(result['binance'])
    assert_poloniex_trades_result(result['poloniex'])


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_trades_errors(rotkehlchen_api_server_with_exchanges):
    """Test errors and edge case of the exchange trades query endpoint"""
    server = rotkehlchen_api_server_with_exchanges
    # invalid exchange
    response = requests.get(api_url_for(
        server,
        "named_exchanges_trades_resource",
        name='boomshakalaka',
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Exchange boomshakalaka is not supported',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # not registered exchange
    response = requests.get(api_url_for(
        server,
        "named_exchanges_trades_resource",
        name='bitmex',
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Could not query trades for bitmex since it is not registered',
        status_code=HTTPStatus.CONFLICT,
    )

    data = {'from_timestamp': 0, 'to_timestamp': 1573409648}
    # TODO: move this into own test
    # from_timestamp being out of range (general test for timestamps field validation)

    data = {'from_timestamp': -1, 'to_timestamp': 1573409648}
    response = requests.get(api_url_for(
        server,
        "named_exchanges_trades_resource",
        name='binance',
    ), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Timestamps can not have negative values',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # from_timestamp not being a valid timestamp type
    data = {'from_timestamp': 'dasd', 'to_timestamp': 1573409648}
    response = requests.get(api_url_for(
        server,
        "named_exchanges_trades_resource",
        name='binance',
    ), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string dasd',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # to_timestamp not being a valid timestamp type
    data = {'from_timestamp': 1, 'to_timestamp': 'dasd'}
    response = requests.get(api_url_for(
        server,
        "named_exchanges_trades_resource",
        name='binance',
    ), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string dasd',
        status_code=HTTPStatus.BAD_REQUEST,
    )
