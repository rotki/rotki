import random
from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
import requests

from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.exchanges.bitfinex import API_KEY_ERROR_MESSAGE as BITFINEX_API_KEY_ERROR_MESSAGE
from rotkehlchen.exchanges.bitstamp import (
    API_KEY_ERROR_CODE_ACTION as BITSTAMP_API_KEY_ERROR_CODE_ACTION,
)
from rotkehlchen.exchanges.data_structures import AssetMovement
from rotkehlchen.exchanges.kucoin import API_KEY_ERROR_CODE_ACTION as KUCOIN_API_KEY_ERROR_CODE
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import FREE_ASSET_MOVEMENTS_LIMIT, FREE_TRADES_LIMIT
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.exchanges import (
    assert_binance_balances_result,
    assert_poloniex_balances_result,
    patch_binance_balances_query,
    patch_poloniex_balances_query,
)
from rotkehlchen.tests.utils.history import (
    assert_binance_trades_result,
    assert_kraken_asset_movements,
    assert_poloniex_asset_movements,
    assert_poloniex_trades_result,
    mock_history_processing_and_exchanges,
    prepare_rotki_for_history_processing_test,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory, Location


def mock_validate_api_key():
    raise ValueError('BOOM 500 ERROR!')


API_KEYPAIR_VALIDATION_PATCH = patch(
    'rotkehlchen.exchanges.kraken.Kraken.validate_api_key',
    return_value=(True, ''),
)
API_KEYPAIR_KRAKEN_VALIDATION_FAIL_PATCH = patch(
    'rotkehlchen.exchanges.kraken.Kraken.validate_api_key',
    side_effect=mock_validate_api_key,
)
API_KEYPAIR_COINBASEPRO_VALIDATION_PATCH = patch(
    'rotkehlchen.exchanges.coinbasepro.Coinbasepro.validate_api_key',
    return_value=(True, ''),
)

API_KEYPAIR_COINBASE_VALIDATION_PATCH = patch(
    'rotkehlchen.exchanges.coinbase.Coinbase.validate_api_key',
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

    # First test that if api key validation fails we get an error, for every exchange
    for name in SUPPORTED_EXCHANGES:
        data = {'name': name, 'api_key': 'ddddd', 'api_secret': 'fffffff'}
        if name in ('coinbasepro', 'kucoin'):
            data['passphrase'] = '123'
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
        assert_error_response(
            response=response,
            contained_in_msg=[
                'Provided API Key or secret is invalid',
                'Provided API Key is invalid',
                'Provided API Key is in invalid Format',
                'Provided API Secret is invalid',
                'Provided Gemini API key needs to have "Auditor" permission activated',
                BITSTAMP_API_KEY_ERROR_CODE_ACTION['API0011'],
                BITFINEX_API_KEY_ERROR_MESSAGE,
                KUCOIN_API_KEY_ERROR_CODE[400003],
            ],
            status_code=HTTPStatus.CONFLICT,
        )
    # Make sure that no exchange is registered after that
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert len(rotki.exchange_manager.connected_exchanges) == 0

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

    # Check that giving a passphrase is fine
    data = {'name': 'coinbasepro', 'api_key': 'ddddd', 'api_secret': 'fffff', 'passphrase': 'sdf'}
    with API_KEYPAIR_COINBASEPRO_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_simple_ok_response(response)
    # and check that coinbasepro is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == ['kraken', 'coinbasepro']


@pytest.mark.parametrize('added_exchanges', [('kraken',)])
def test_kraken_malformed_response(rotkehlchen_api_server_with_exchanges):
    """Test that if Rotki gets a malformed response from Kraken it's handled properly

    Regression test for the first part of https://github.com/rotki/rotki/issues/943
    and for https://github.com/rotki/rotki/issues/946
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    kraken = rotki.exchange_manager.get('kraken')
    kraken.cache_ttl_secs = 0
    kraken.use_original_kraken = True
    response_data = '{"'

    def mock_kraken_return(url, *args, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, response_data)
    kraken_patch = patch.object(kraken.session, 'post', side_effect=mock_kraken_return)

    # Test that invalid json is handled
    with kraken_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "exchangebalancesresource",
                name='kraken',
            ),
        )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Could not reach kraken due to Invalid JSON in Kraken response',
    )

    # Test that the response missing result key seen in #946 is handled properly
    response_data = '{"error": []}'
    with kraken_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                "exchangebalancesresource",
                name='kraken',
            ),
        )
    assert_proper_response(response=response)
    data = response.json()
    assert data['result'] == {}
    assert data['message'] == ""


def test_setup_exchange_does_not_stay_in_mapping_after_500_error(rotkehlchen_api_server):
    """Test that if 500 error is returned during setup of an exchange and it's stuck
    in the exchange mapping Rotki doesn't still think the exchange is registered.

    Regression test for the second part of https://github.com/rotki/rotki/issues/943
    """
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_KRAKEN_VALIDATION_FAIL_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    )

    # Now try to register the exchange again
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
        contained_in_msg='Given API Key should be a string',
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
        contained_in_msg='Given API Secret should be a string',
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
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    # Setup coinbase exchange
    data = {'name': 'coinbase', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_COINBASE_VALIDATION_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data,
        )
    assert_simple_ok_response(response)

    # Add query ranges to see that they also get deleted when removing the exchange
    cursor = db.conn.cursor()
    cursor.executemany(
        'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
        [('coinbasepro_trades', 0, 1579564096),
         ('coinbasepro_margins', 0, 1579564096),
         ('coinbasepro_asset_movements', 0, 1579564096),
         ('coinbase_trades', 0, 1579564096),
         ('coinbase_margins', 0, 1579564096),
         ('coinbase_asset_movements', 0, 1579564096),
         ('binance_trades', 0, 1579564096),
         ('binance_margins', 0, 1579564096),
         ('binance_asset_movements', 0, 1579564096)],
    )

    # Now remove the registered coinbase exchange
    data = {'name': 'coinbase'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"), json=data)
    assert_simple_ok_response(response)
    # and check that it's not registered anymore
    response = requests.get(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == []
    # Also check that the coinbase query ranges have been deleted but not the other ones
    cursor = db.conn.cursor()
    result = cursor.execute('SELECT name from used_query_ranges')
    count = 0
    for entry in result:
        count += 1
        msg = 'only binance or coinbasepro query ranges should remain'
        assert 'binance' in entry[0] or 'coinbasepro' in entry[0], msg
    assert count == 6, 'only 6 query ranges should remain in the DB'

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
    response = requests.delete(api_url_for(rotkehlchen_api_server, "exchangesresource"))
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_balances(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange balances query endpoint works fine"""
    async_query = random.choice([False, True])
    # query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['binance']

    binance_patch = patch_binance_balances_query(binance)
    with binance_patch:
        response = requests.get(api_url_for(
            server,
            "named_exchanges_balances_resource",
            name='binance',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)
    assert_binance_balances_result(outcome)

    # query balances of all setup exchanges
    poloniex = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['poloniex']

    poloniex_patch = patch_poloniex_balances_query(poloniex)
    with binance_patch, poloniex_patch:
        response = requests.get(
            api_url_for(server, "exchangebalancesresource"),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    assert_binance_balances_result(result['binance'])
    assert_poloniex_balances_result(result['poloniex'])


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_balances_ignore_cache(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange balances query endpoint can ignore cache"""
    server = rotkehlchen_api_server_with_exchanges
    binance = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges['binance']
    binance_patch = patch_binance_balances_query(binance)
    binance_api_query = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)

    with binance_patch, binance_api_query as bn:
        # Query balances for the first time
        response = requests.get(api_url_for(
            server,
            "named_exchanges_balances_resource",
            name='binance',
        ))
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == ''
        assert_binance_balances_result(json_data['result'])
        assert bn.call_count == 3
        # Do the query again. Cache should be used.
        binance_patch = patch_binance_balances_query(binance)
        response = requests.get(api_url_for(
            server,
            "named_exchanges_balances_resource",
            name='binance',
        ))
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == ''
        assert_binance_balances_result(json_data['result'])
        assert bn.call_count == 3, 'call count should not have changed. Cache must have been used'
        # Finally do the query and request ignoring of the cache
        binance_patch = patch_binance_balances_query(binance)
        response = requests.get(api_url_for(
            server,
            "named_exchanges_balances_resource",
            name='binance',
        ), json={'ignore_cache': True})
        assert_proper_response(response)
        json_data = response.json()
        assert json_data['message'] == ''
        assert_binance_balances_result(json_data['result'])
        assert bn.call_count == 6, 'call count should have changed. Cache should have been ignored'


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


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_exchange_query_trades(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange trades query endpoint works fine"""
    async_query = random.choice([False, True])
    server = rotkehlchen_api_server_with_exchanges
    setup = mock_history_processing_and_exchanges(server.rest_api.rotkehlchen)
    # query trades of one specific exchange
    with setup.binance_patch:
        response = requests.get(
            api_url_for(
                server,
                "tradesresource",
            ), json={'location': 'binance', 'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)
    assert result['entries_found'] > 0
    assert result['entries_limit'] == FREE_TRADES_LIMIT
    assert_binance_trades_result([x['entry'] for x in result['entries']])

    # query trades of all exchanges
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(server, "tradesresource"),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    trades = result['entries']
    assert_binance_trades_result([x['entry'] for x in trades if x['entry']['location'] == 'binance'])  # noqa: E501
    assert_poloniex_trades_result([x['entry'] for x in trades if x['entry']['location'] == 'poloniex'])  # noqa: E501

    def assert_okay(response):
        """Helper function for DRY checking below assertions"""
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)
        trades = result['entries']
        assert_binance_trades_result([x['entry'] for x in trades if x['entry']['location'] == 'binance'])  # noqa: E501
        assert_poloniex_trades_result(
            trades=[x['entry'] for x in trades if x['entry']['location'] == 'poloniex'],
            trades_to_check=(2,),
        )

    # and now query them in a specific time range excluding two of poloniex's trades
    data = {'from_timestamp': 1499865548, 'to_timestamp': 1539713118, 'async_query': async_query}
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(api_url_for(server, "tradesresource"), json=data)
        assert_okay(response)
    # do the same but with query args. This serves as test of from/to timestamp with query args
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(server, "tradesresource") + '?' + urlencode(data))
        assert_okay(response)


@pytest.mark.parametrize('added_exchanges', [('kraken', 'poloniex')])
def test_query_asset_movements(rotkehlchen_api_server_with_exchanges):
    """Test that using the asset movements query endpoint works fine"""
    async_query = random.choice([False, True])
    server = rotkehlchen_api_server_with_exchanges
    setup = prepare_rotki_for_history_processing_test(server.rest_api.rotkehlchen)
    # setup = mock_history_processing_and_exchanges(server.rest_api.rotkehlchen)
    # query asset movements of one specific exchange
    with setup.polo_patch:
        response = requests.get(
            api_url_for(
                server,
                "assetmovementsresource",
            ), json={'location': 'poloniex', 'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 4
    assert result['entries_limit'] == FREE_ASSET_MOVEMENTS_LIMIT
    poloniex_ids = [x['entry']['identifier'] for x in result['entries']]
    assert_poloniex_asset_movements([x['entry'] for x in result['entries']], deserialized=True)
    assert all(x['ignored_in_accounting'] is False for x in result['entries']), 'ignored should be false'  # noqa: E501

    # now let's ignore all poloniex action ids
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "ignoredactionsresource",
        ), json={'action_type': 'asset movement', 'action_ids': poloniex_ids},
    )
    result = assert_proper_response_with_result(response)
    assert set(result['asset movement']) == set(poloniex_ids)

    # query asset movements of all exchanges
    with setup.polo_patch:
        response = requests.get(
            api_url_for(server, "assetmovementsresource"),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    movements = result['entries']
    assert_poloniex_asset_movements([x['entry'] for x in movements if x['entry']['location'] == 'poloniex'], True)  # noqa: E501
    assert_kraken_asset_movements([x['entry'] for x in movements if x['entry']['location'] == 'kraken'], True)  # noqa: E501

    def assert_okay(response):
        """Helper function for DRY checking below assertions"""
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)
        movements = result['entries']
        assert_poloniex_asset_movements(
            to_check_list=[x['entry'] for x in movements if x['entry']['location'] == 'poloniex'],
            deserialized=True,
            movements_to_check=(1, 2),
        )
        msg = 'poloniex asset movements should have now been ignored for accounting'
        assert all(x['ignored_in_accounting'] is True for x in movements if x['entry']['location'] == 'poloniex'), msg  # noqa: E501
        assert_kraken_asset_movements(
            to_check_list=[x['entry'] for x in movements if x['entry']['location'] == 'kraken'],
            deserialized=True,
            movements_to_check=(0, 1, 2),
        )

    # and now query them in a specific time range excluding some asset movements
    data = {'from_timestamp': 1439994442, 'to_timestamp': 1458994442, 'async_query': async_query}
    with setup.polo_patch:
        response = requests.get(api_url_for(server, "assetmovementsresource"), json=data)
        assert_okay(response)
    # do the same but with query args. This serves as test of from/to timestamp with query args
    with setup.polo_patch:
        response = requests.get(
            api_url_for(server, "assetmovementsresource") + '?' + urlencode(data))
        assert_okay(response)


@pytest.mark.parametrize('added_exchanges', [('kraken', 'poloniex')])
@pytest.mark.parametrize('start_with_valid_premium', [False, True])
def test_query_asset_movements_over_limit(
        rotkehlchen_api_server_with_exchanges,
        start_with_valid_premium,
):
    """Test that using the asset movements query endpoint works fine"""
    start_ts = 0
    end_ts = 1598453214
    server = rotkehlchen_api_server_with_exchanges
    rotki = server.rest_api.rotkehlchen
    # Make sure online kraken is not queried by setting query ranges
    rotki.data.db.update_used_query_range(
        name='kraken_asset_movements',
        start_ts=start_ts,
        end_ts=end_ts,
    )
    polo_entries_num = 4
    # Set a ton of kraken asset movements in the DB
    kraken_entries_num = FREE_ASSET_MOVEMENTS_LIMIT + 50
    movements = [AssetMovement(
        location=Location.KRAKEN,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id=None,
        timestamp=x,
        asset=A_BTC,
        amount=FVal(x * 100),
        fee_asset=A_BTC,
        fee=FVal(x),
        link='') for x in range(kraken_entries_num)
    ]
    rotki.data.db.add_asset_movements(movements)
    all_movements_num = kraken_entries_num + polo_entries_num
    setup = prepare_rotki_for_history_processing_test(server.rest_api.rotkehlchen)

    # Check that querying movements with/without limits works even if we query two times
    for _ in range(2):
        # query asset movements of polo which has less movements than the limit
        with setup.polo_patch:
            response = requests.get(
                api_url_for(
                    server,
                    "assetmovementsresource",
                ), json={'location': 'poloniex'},
            )
        result = assert_proper_response_with_result(response)
        assert result['entries_found'] == all_movements_num
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_ASSET_MOVEMENTS_LIMIT  # noqa: E501
        assert_poloniex_asset_movements([x['entry'] for x in result['entries']], deserialized=True)

        # now query kraken which has a ton of DB entries
        response = requests.get(
            api_url_for(server, "assetmovementsresource"),
            json={'location': 'kraken'},
        )
        result = assert_proper_response_with_result(response)

        if start_with_valid_premium:
            assert len(result['entries']) == kraken_entries_num
            assert result['entries_limit'] == -1
            assert result['entries_found'] == all_movements_num
        else:
            assert len(result['entries']) == FREE_ASSET_MOVEMENTS_LIMIT - polo_entries_num
            assert result['entries_limit'] == FREE_ASSET_MOVEMENTS_LIMIT
            assert result['entries_found'] == all_movements_num
