import os
import random
from http import HTTPStatus
from typing import TYPE_CHECKING, cast
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_BUSD, A_DAI, A_ETH, A_EUR, A_USDT
from rotkehlchen.constants.limits import FREE_ASSET_MOVEMENTS_LIMIT, FREE_TRADES_LIMIT
from rotkehlchen.db.constants import KRAKEN_ACCOUNT_TYPE_KEY
from rotkehlchen.db.filtering import AssetMovementsFilterQuery, TradesFilterQuery
from rotkehlchen.db.history_events import HISTORY_BASE_ENTRY_FIELDS, DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.exchanges.bitfinex import API_KEY_ERROR_MESSAGE as BITFINEX_API_KEY_ERROR_MESSAGE
from rotkehlchen.exchanges.bitstamp import (
    API_KEY_ERROR_CODE_ACTION as BITSTAMP_API_KEY_ERROR_CODE_ACTION,
)
from rotkehlchen.exchanges.constants import EXCHANGES_WITH_PASSPHRASE, SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.kraken import DEFAULT_KRAKEN_ACCOUNT_TYPE, Kraken, KrakenAccountType
from rotkehlchen.exchanges.kucoin import API_KEY_ERROR_CODE_ACTION as KUCOIN_API_KEY_ERROR_CODE
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.binance import GlobalDBBinance
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
    mock_api_query_for_binance_lending,
    patch_binance_balances_query,
    patch_poloniex_balances_query,
    try_get_first_exchange,
)
from rotkehlchen.tests.utils.factories import make_random_uppercasenumeric_string
from rotkehlchen.tests.utils.history import (
    assert_binance_trades_result,
    assert_kraken_asset_movements,
    assert_poloniex_asset_movements,
    assert_poloniex_trades_result,
    mock_history_processing_and_exchanges,
    prepare_rotki_for_history_processing_test,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import AssetMovementCategory, Location, Timestamp, TimestampMS, TradeType

if TYPE_CHECKING:
    from requests import Response

    from rotkehlchen.api.server import APIServer


def mock_validate_api_key():
    raise ValueError('BOOM ERROR!')


API_KEYPAIR_KRAKEN_VALIDATION_FAIL_PATCH = patch(
    'rotkehlchen.exchanges.kraken.Kraken.validate_api_key',
    side_effect=mock_validate_api_key,
)


def mock_validate_api_key_success(location: Location):
    name = str(location)
    if location == Location.BINANCEUS:
        name = 'binance'
    return patch(
        f'rotkehlchen.exchanges.{name}.{name.capitalize()}.validate_api_key',
        return_value=(True, ''),
    )


def mock_validate_api_key_failure(location: Location):
    name = str(location)
    if location == Location.BINANCEUS:
        name = 'binance'
    return patch(
        f'rotkehlchen.exchanges.{name}.{name.capitalize()}.validate_api_key',
        side_effect=mock_validate_api_key,
    )


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='Dont query all production exchanges when CI runs',
)
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_setup_exchange(rotkehlchen_api_server):
    """Test that setting up an exchange via the api works

    Hits all production exchange servers with a query to make sure that the api key
    validation error of each exchange is handled properly.
    """
    # Check that no exchanges are registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert json_data['result'] == []

    # First test that if api key validation fails we get an error, for every exchange
    api_key = make_random_uppercasenumeric_string(size=10)
    api_secret = make_random_uppercasenumeric_string(size=10)
    for location in SUPPORTED_EXCHANGES:
        data = {
            'location': str(location),
            'name': f'my_{location!s}',
            'api_key': api_key,
            'api_secret': api_secret,
        }
        if location in EXCHANGES_WITH_PASSPHRASE:
            data['passphrase'] = '123'
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
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
                'Error validating API Keys',
                'ApiKey has invalid value',
                'Error validating Bitpanda API Key',
                '',  # poloniex fails with no error message now
            ],
            status_code=HTTPStatus.CONFLICT,
        )
    # Make sure that no exchange is registered after that
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert len(rotki.exchange_manager.connected_exchanges) == 0

    # Mock the api pair validation and make sure that the exchange is setup
    data = {'location': 'kraken', 'name': 'my_kraken', 'api_key': api_key, 'api_secret': api_secret}  # noqa: E501
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_simple_ok_response(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    result = assert_proper_response_with_result(response)
    assert result == [{'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'}]  # noqa: E501

    # Check that we get an error if we try to re-setup an already setup exchange
    data = {'location': 'kraken', 'name': 'my_kraken', 'api_key': api_key, 'api_secret': api_secret}  # noqa: E501
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='kraken exchange my_kraken is already registered',
        status_code=HTTPStatus.CONFLICT,
    )

    # But check that same location different name works
    data = {'location': 'kraken', 'name': 'my_other_kraken', 'api_key': 'aadddddd', 'api_secret': 'fffffff'}  # noqa: E501
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_simple_ok_response(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    result = assert_proper_response_with_result(response)
    assert result == [
        {'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},
        {'location': 'kraken', 'name': 'my_other_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},
    ]

    # Check that giving a passphrase is fine
    data = {'location': 'coinbasepro', 'name': 'my_coinbasepro', 'api_key': api_key, 'api_secret': api_secret, 'passphrase': 'sdf'}  # noqa: E501
    with mock_validate_api_key_success(Location.COINBASEPRO):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_simple_ok_response(response)
    # and check that coinbasepro is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    result = assert_proper_response_with_result(response)
    assert result == [
        {'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},
        {'location': 'kraken', 'name': 'my_other_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},
        {'location': 'coinbasepro', 'name': 'my_coinbasepro'},
    ]


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
def test_kraken_malformed_response(rotkehlchen_api_server_with_exchanges):
    """Test that if rotki gets a malformed response from Kraken it's handled properly

    Regression test for the first part of https://github.com/rotki/rotki/issues/943
    and for https://github.com/rotki/rotki/issues/946
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    kraken = try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN)
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
                'exchangebalancesresource',
                location='kraken',
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
                'exchangebalancesresource',
                location='kraken',
            ),
        )
    result = assert_proper_response_with_result(response=response)
    assert result == {}


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_setup_exchange_does_not_stay_in_mapping_after_500_error(rotkehlchen_api_server):
    """Test that if 500 error is returned during setup of an exchange and it's stuck
    in the exchange mapping rotki doesn't still think the exchange is registered.

    Regression test for the second part of https://github.com/rotki/rotki/issues/943
    """
    data = {'location': 'kraken', 'name': 'my_kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with API_KEYPAIR_KRAKEN_VALIDATION_FAIL_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
    )

    # Now try to register the exchange again
    data = {'location': 'kraken', 'name': 'my_kraken', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_simple_ok_response(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    result = assert_proper_response_with_result(response)
    assert result == [{'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'}]  # noqa: E501


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_setup_exchange_errors(rotkehlchen_api_server):
    """Test errors and edge cases of setup_exchange endpoint"""

    # Provide unsupported exchange location
    data = {'location': 'notexisting', 'name': 'foo', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value notexisting',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type exchange location
    data = {'location': 3434, 'name': 'foo', 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value from non string value: 3434',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type exchange name
    data = {'location': 'kraken', 'name': 55, 'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit exchange name and location
    data = {'api_key': 'ddddd', 'api_secret': 'fffffff'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for api key
    data = {'name': 'kraken', 'api_key': True, 'api_secret': 'fffffff'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Given API Key should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api key
    data = {'name': 'kraken', 'api_secret': 'fffffff'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type for api secret
    data = {'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 234.1}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Given API Secret should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api secret
    data = {'name': 'kraken', 'api_key': 'ddddd'}
    with mock_validate_api_key_success(Location.KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_exchange(rotkehlchen_api_server):
    """Test that removing a setup exchange via the api works"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    # Setup coinbase exchange
    data = {
        'location': 'coinbase',
        'name': 'Coinbase 1',
        'api_key': 'ddddd',
        'api_secret': 'fffffff',
    }
    with mock_validate_api_key_success(Location.COINBASE):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_simple_ok_response(response)
    # and check it's registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    result = assert_proper_response_with_result(response)
    assert result == [{'location': 'coinbase', 'name': 'Coinbase 1'}]

    # Add query ranges to see that they also get deleted when removing the exchange
    cursor = db.conn.cursor()
    cursor.executemany(
        'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
        [('coinbasepro_trades_CoinbasePro 1', 0, 1579564096),
         ('coinbasepro_margins_CoinbasePro 1', 0, 1579564096),
         ('coinbasepro_asset_movements_CoinbasePro 1', 0, 1579564096),
         ('coinbase_trades_Coinbase 1', 0, 1579564096),
         ('coinbase_margins_Coinbase 1', 0, 1579564096),
         ('coinbase_asset_movements_Coinbase 1', 0, 1579564096),
         ('coinbase_trades_Coinbase 2', 0, 1579564096),
         ('coinbase_margins_Coinbase 2', 0, 1579564096),
         ('coinbase_asset_movements_Coinbase 2', 0, 1579564096),
         ('binance_trades_Binance 1', 0, 1579564096),
         ('binance_margins_Binance 1', 0, 1579564096),
         ('binance_asset_movements_Binance 1', 0, 1579564096)],
    )

    # Now remove the registered coinbase exchange
    data = {'location': 'coinbase', 'name': 'Coinbase 1'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data)
    assert_simple_ok_response(response)
    # and check that it's not registered anymore
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    result = assert_proper_response_with_result(response)
    assert result == []
    # Also check that the coinbase query ranges have been deleted but not the other ones
    cursor = db.conn.cursor()
    result = cursor.execute('SELECT name from used_query_ranges')
    count = 0
    for entry in result:
        count += 1
        msg = 'only binance or coinbasepro or Coinbase 2 query ranges should remain'
        assert 'binance' in entry[0] or 'coinbasepro' in entry[0] or 'Coinbase 2' in entry[0], msg
    assert count == 9, 'only 9 query ranges should remain in the DB'

    # now try to remove a non-registered exchange
    data = {'location': 'binance', 'name': 'my_binance'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='binance exchange my_binance is not registered',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_exchange_errors(rotkehlchen_api_server):
    """Errors and edge cases when using the remove exchange endpoint"""
    # remove unsupported exchange
    data = {'location': 'wowexchange', 'name': 'foo'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value wowexchange',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for exchange location
    data = {'location': 5533, 'name': 'foo'}
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value from non string value',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # invalid type for exchange name
    data = {'location': 'kraken', 'name': 55}
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # omit exchange location at removal
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_exchange_query_balances(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange balances query endpoint works fine"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    # query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)

    binance_patch = patch_binance_balances_query(binance)
    with binance_patch:
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)
    assert_binance_balances_result(outcome)

    # query balances of all setup exchanges
    poloniex = try_get_first_exchange(rotki.exchange_manager, Location.POLONIEX)
    poloniex_patch = patch_poloniex_balances_query(poloniex)
    with binance_patch, poloniex_patch:
        response = requests.get(
            api_url_for(server, 'exchangebalancesresource'),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(server, task_id)
        else:
            result = assert_proper_response_with_result(response)

    assert_binance_balances_result(result['binance'])
    assert_poloniex_balances_result(result['poloniex'])


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_exchange_query_balances_ignore_cache(rotkehlchen_api_server_with_exchanges):
    """Test that using the exchange balances query endpoint can ignore cache"""
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    binance = try_get_first_exchange(rotki.exchange_manager, Location.BINANCE)
    binance_patch = patch_binance_balances_query(binance)
    binance_api_query = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)

    with binance_patch, binance_api_query as bn:
        # Query balances for the first time
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ))
        result = assert_proper_response_with_result(response)
        assert_binance_balances_result(result)
        assert bn.call_count == 3
        # Do the query again. Cache should be used.
        binance_patch = patch_binance_balances_query(binance)
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ))
        result = assert_proper_response_with_result(response)
        assert_binance_balances_result(result)
        assert bn.call_count == 3, 'call count should not have changed. Cache must have been used'
        # Finally do the query and request ignoring of the cache
        binance_patch = patch_binance_balances_query(binance)
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'ignore_cache': True})
        result = assert_proper_response_with_result(response)
        assert_binance_balances_result(result)
        assert bn.call_count == 6, 'call count should have changed. Cache should have been ignored'


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_exchange_query_balances_errors(rotkehlchen_api_server_with_exchanges):
    """Test errors and edge cases of the exchange balances query endpoint"""
    server = rotkehlchen_api_server_with_exchanges
    # Invalid exchange
    response = requests.get(api_url_for(
        server,
        'named_exchanges_balances_resource',
        location='dasdsad',
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value dasdsad',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # not registered exchange
    response = requests.get(api_url_for(
        server,
        'named_exchanges_balances_resource',
        location='kraken',
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Could not query balances for kraken since it is not registered',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_exchange_query_trades(rotkehlchen_api_server_with_exchanges: 'APIServer'):
    """Test that using the exchange trades query endpoint works fine"""
    async_query = random.choice([False, True])
    server = rotkehlchen_api_server_with_exchanges
    setup = mock_history_processing_and_exchanges(server.rest_api.rotkehlchen)
    # query trades of one specific exchange
    with setup.binance_patch:
        response = requests.get(
            api_url_for(
                server,
                'tradesresource',
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
            api_url_for(server, 'tradesresource'),
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

    def assert_okay(response: 'Response'):
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
        response = requests.get(api_url_for(server, 'tradesresource'), json=data)
        assert_okay(response)
    # do the same but with query args. This serves as test of from/to timestamp with query args
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(server, 'tradesresource') + '?' + urlencode(data))
        assert_okay(response)

    # check that for poloniex we have information
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            url=api_url_for(server, 'tradesresource'),
            json={'location': 'poloniex'},
        )

    result = assert_proper_response_with_result(response)
    assert len(result['entries']) != 0

    # exclude poloniex as location and delete the trades from there
    db = server.rest_api.rotkehlchen.data.db
    poloniex_exchange = server.rest_api.rotkehlchen.exchange_manager.connected_exchanges[Location.POLONIEX][0]  # noqa: E501
    with db.user_write() as cursor:
        db.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[poloniex_exchange.location_id()],
        ))
        # delete poloniex information to verify that when querying the location no new
        # trades are queried
        db.purge_exchange_data(cursor, Location.POLONIEX)

    # query the API and check that information is not queried again
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            url=api_url_for(server, 'tradesresource'),
            json={'location': 'poloniex'},
        )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 0


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN, Location.POLONIEX)])
@pytest.mark.parametrize('start_with_valid_premium', [False, True])
def test_query_asset_movements(rotkehlchen_api_server_with_exchanges, start_with_valid_premium):
    """Test that using the asset movements query endpoint works fine"""
    async_query = random.choice([False, True])
    server = rotkehlchen_api_server_with_exchanges
    setup = prepare_rotki_for_history_processing_test(server.rest_api.rotkehlchen)
    # query asset movements of one specific exchange
    with setup.polo_patch:
        response = requests.get(
            api_url_for(
                server,
                'assetmovementsresource',
            ), json={'location': 'poloniex', 'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)
    assert result['entries_found'] == 4
    assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_ASSET_MOVEMENTS_LIMIT  # noqa: E501
    poloniex_ids = [x['entry']['identifier'] for x in result['entries']]
    assert_poloniex_asset_movements([x['entry'] for x in result['entries']], deserialized=True)
    assert all(x['ignored_in_accounting'] is False for x in result['entries']), 'ignored should be false'  # noqa: E501

    # now let's ignore all poloniex action ids
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredactionsresource',
        ), json={'action_type': 'asset_movement', 'data': poloniex_ids},
    )
    assert_simple_ok_response(response)
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor, None)
    assert set(result[ActionType.ASSET_MOVEMENT]) == set(poloniex_ids)

    # query asset movements of all exchanges
    with setup.polo_patch:
        response = requests.get(
            api_url_for(server, 'assetmovementsresource'),
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
            movements_to_check=(0, 1, 2, 3, 4),
        )

    # and now query them in a specific time range excluding some asset movements
    data = {'from_timestamp': 1439994442, 'to_timestamp': 1458994442, 'async_query': async_query}
    with setup.polo_patch:
        response = requests.get(api_url_for(server, 'assetmovementsresource'), json=data)
        assert_okay(response)
    # do the same but with query args. This serves as test of from/to timestamp with query args
    with setup.polo_patch:
        response = requests.get(
            api_url_for(server, 'assetmovementsresource') + '?' + urlencode(data))
        assert_okay(response)

    # and now test pagination
    data = {'only_cache': True, 'offset': 1, 'limit': 2, 'location': 'kraken'}
    response = requests.get(api_url_for(server, 'assetmovementsresource'), json=data)
    result = assert_proper_response_with_result(response)
    assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_ASSET_MOVEMENTS_LIMIT  # noqa: E501
    assert result['entries_found'] == 6
    assert result['entries_total'] == 10
    movements = result['entries']
    assert len(movements) == 2
    assert_kraken_asset_movements(
        to_check_list=[x['entry'] for x in movements if x['entry']['location'] == 'kraken'],
        deserialized=True,
        movements_to_check=(1, 2),
    )

    def assert_order_by(order_by: str):
        """A helper to keep things DRY in the test"""
        data = {'order_by_attributes': [order_by], 'ascending': [False], 'only_cache': True}
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'assetmovementsresource',
            ), json=data,
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_ASSET_MOVEMENTS_LIMIT  # noqa: E501
        assert result['entries_total'] == 10
        assert result['entries_found'] == 10
        desc_result = result['entries']
        assert len(desc_result) == 10
        data = {'order_by_attributes': [order_by], 'ascending': [True], 'only_cache': True}
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'assetmovementsresource',
            ), json=data,
        )
        result = assert_proper_response_with_result(response)
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_ASSET_MOVEMENTS_LIMIT  # noqa: E501
        assert result['entries_total'] == 10
        assert result['entries_found'] == 10
        asc_result = result['entries']
        assert len(asc_result) == 10
        return desc_result, asc_result

    # test order by location
    desc_result, asc_result = assert_order_by('location')
    assert all(x['entry']['location'] == 'poloniex' for x in desc_result[:4])
    assert all(x['entry']['location'] == 'kraken' for x in desc_result[4:])
    assert all(x['entry']['location'] == 'kraken' for x in asc_result[:6])
    assert all(x['entry']['location'] == 'poloniex' for x in asc_result[6:])

    # test order by category
    desc_result, asc_result = assert_order_by('category')
    assert all(x['entry']['category'] == 'withdrawal' for x in desc_result[:5])
    assert all(x['entry']['category'] == 'deposit' for x in desc_result[5:])
    assert all(x['entry']['category'] == 'deposit' for x in asc_result[:5])
    assert all(x['entry']['category'] == 'withdrawal' for x in asc_result[5:])

    # test order by amount
    desc_result, asc_result = assert_order_by('amount')
    for idx, x in enumerate(desc_result):
        if idx < len(desc_result) - 1:
            assert FVal(x['entry']['amount']) >= FVal(desc_result[idx + 1]['entry']['amount'])
    for idx, x in enumerate(asc_result):
        if idx < len(asc_result) - 1:
            assert FVal(x['entry']['amount']) <= FVal(asc_result[idx + 1]['entry']['amount'])

    # test order by fee
    desc_result, asc_result = assert_order_by('fee')
    for idx, x in enumerate(desc_result):
        if idx < len(desc_result) - 1:
            assert FVal(x['entry']['fee']) >= FVal(desc_result[idx + 1]['entry']['fee'])
    for idx, x in enumerate(asc_result):
        if idx < len(asc_result) - 1:
            assert FVal(x['entry']['fee']) <= FVal(asc_result[idx + 1]['entry']['fee'])


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN, Location.POLONIEX)])
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
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.update_used_query_range(
            write_cursor=cursor,
            name='kraken_asset_movements_mockkraken',
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
        rotki.data.db.add_asset_movements(cursor, movements)

    all_movements_num = kraken_entries_num + polo_entries_num
    setup = prepare_rotki_for_history_processing_test(server.rest_api.rotkehlchen)

    # Check that querying movements with/without limits works even if we query two times
    for _ in range(2):
        # query asset movements of polo which has less movements than the limit
        with setup.polo_patch:
            response = requests.get(
                api_url_for(
                    server,
                    'assetmovementsresource',
                ), json={'location': 'poloniex'},
            )
        result = assert_proper_response_with_result(response)
        assert result['entries_found'] == polo_entries_num
        assert result['entries_total'] == all_movements_num
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_ASSET_MOVEMENTS_LIMIT  # noqa: E501
        assert_poloniex_asset_movements([x['entry'] for x in result['entries']], deserialized=True)

        # now query kraken which has a ton of DB entries
        response = requests.get(
            api_url_for(server, 'assetmovementsresource'),
            json={'location': 'kraken'},
        )
        result = assert_proper_response_with_result(response)

        if start_with_valid_premium:
            assert len(result['entries']) == kraken_entries_num
            assert result['entries_limit'] == -1
            assert result['entries_found'] == kraken_entries_num
            assert result['entries_total'] == all_movements_num
        else:
            assert len(result['entries']) == FREE_ASSET_MOVEMENTS_LIMIT - polo_entries_num
            assert result['entries_limit'] == FREE_ASSET_MOVEMENTS_LIMIT
            assert result['entries_found'] == kraken_entries_num
            assert result['entries_total'] == all_movements_num


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_delete_external_exchange_data_works(rotkehlchen_api_server_with_exchanges):
    server = rotkehlchen_api_server_with_exchanges
    rotki = server.rest_api.rotkehlchen

    trades = [Trade(
        timestamp=0,
        location=x,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=ONE,
        rate=ONE,
        fee=ONE,
        fee_currency=A_EUR,
        link='',
        notes='',
    ) for x in (Location.CRYPTOCOM, Location.KRAKEN)]
    movements = [AssetMovement(
        location=x,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id=None,
        timestamp=0,
        asset=A_BTC,
        amount=FVal(100),
        fee_asset=A_BTC,
        fee=ONE,
        link='') for x in (Location.CRYPTOCOM, Location.KRAKEN)]
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_trades(cursor, trades)
        rotki.data.db.add_asset_movements(cursor, movements)

        assert len(rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)) == 2  # noqa: E501
        assert len(rotki.data.db.get_asset_movements(
            cursor,
            filter_query=AssetMovementsFilterQuery.make(),
            has_premium=True,
        )) == 2
    response = requests.delete(
        api_url_for(
            server,
            'named_exchanges_data_resource',
            location='cryptocom',
        ),
    )
    result = assert_proper_response_with_result(response)  # just check no validation error happens
    assert result is True
    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(rotki.data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)) == 1  # noqa: E501
        assert len(rotki.data.db.get_asset_movements(
            cursor,
            filter_query=AssetMovementsFilterQuery.make(),
            has_premium=True,
        )) == 1


@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN, Location.POLONIEX)])
def test_edit_exchange_account(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    db = rotki.data.db
    event_db = DBHistoryEvents(db)

    kraken = try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN)
    poloniex = try_get_first_exchange(rotki.exchange_manager, Location.POLONIEX)
    assert kraken is not None
    assert poloniex is not None
    kraken = cast(Kraken, kraken)
    assert kraken.name == 'mockkraken'
    assert kraken.account_type == DEFAULT_KRAKEN_ACCOUNT_TYPE
    assert poloniex.name == 'poloniex'

    # test event to check that editing an exchange with history events edits the location label
    test_event = HistoryEvent(
        event_identifier='STARK-STARK-STARK',
        sequence_index=0,
        timestamp=TimestampMS(1673146287380),
        location=Location.KRAKEN,
        location_label=kraken.name,
        asset=A_ETH,
        balance=Balance(
            amount=FVal('0.0000400780'),
            usd_value=FVal('0.051645312360'),
        ),
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        notes='Staking reward from kraken',
    )

    # add some exchanges ranges
    start_ts, end_ts = Timestamp(0), Timestamp(9999)
    with db.user_write() as cursor:
        db.update_used_query_range(cursor, name=f'{Location.KRAKEN!s}_trades_mockkraken', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name=f'{Location.KRAKEN!s}_margins_mockkraken', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name=f'{Location.KRAKEN!s}_asset_movements_mockkraken', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name=f'{Location.KRAKEN!s}_margins_kraken_boi', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name=f'{Location.KRAKEN!s}_asset_movements_kraken_boi', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name=f'{Location.POLONIEX!s}_trades_poloniex', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name=f'{Location.POLONIEX!s}_margins_poloniex', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name=f'{Location.POLONIEX!s}_asset_movements_poloniex', start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        db.update_used_query_range(cursor, name='uniswap_trades', start_ts=start_ts, end_ts=end_ts)
        test_event_id = event_db.add_history_event(write_cursor=cursor, event=test_event)

    data = {
        'name': 'mockkraken',
        'location': 'kraken',
        'new_name': 'my_kraken',
        'kraken_account_type': KrakenAccountType.STARTER.serialize(),
    }
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_response_with_result(response)
    assert result is True
    assert kraken is not None
    assert kraken.name == 'my_kraken'
    assert kraken.account_type == DEFAULT_KRAKEN_ACCOUNT_TYPE

    # check that queryranges were succesfuly updated and the others were unmodified
    expected_ranges_tuple = (start_ts, end_ts)
    with db.conn.read_ctx() as cursor:
        assert db.get_used_query_range(cursor, 'kraken_trades_mockkraken') is None
        assert db.get_used_query_range(cursor, 'kraken_margins_mockkraken') is None
        assert db.get_used_query_range(cursor, 'kraken_asset_movements_mockkraken') is None
        assert db.get_used_query_range(cursor, 'kraken_trades_my_kraken') == expected_ranges_tuple
        assert db.get_used_query_range(cursor, 'kraken_margins_my_kraken') == expected_ranges_tuple
        assert db.get_used_query_range(cursor, 'kraken_asset_movements_my_kraken') == expected_ranges_tuple  # noqa: E501
        assert db.get_used_query_range(cursor, 'poloniex_trades_poloniex') == expected_ranges_tuple
        assert db.get_used_query_range(cursor, 'poloniex_margins_poloniex') == expected_ranges_tuple  # noqa: E501
        assert db.get_used_query_range(cursor, 'poloniex_asset_movements_poloniex') == expected_ranges_tuple  # noqa: E501

        data = {'name': 'poloniex', 'location': 'poloniex', 'new_name': 'my_poloniex'}
        response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
        result = assert_proper_response_with_result(response)
        assert result is True
        poloniex = try_get_first_exchange(rotki.exchange_manager, Location.POLONIEX)
        assert poloniex is not None
        assert poloniex.name == 'my_poloniex'
        assert db.get_used_query_range(cursor, 'poloniex_trades_my_poloniex') == expected_ranges_tuple  # noqa: E501
        assert db.get_used_query_range(cursor, 'poloniex_margins_my_poloniex') == expected_ranges_tuple  # noqa: E501
        assert db.get_used_query_range(cursor, 'poloniex_asset_movements_my_poloniex') == expected_ranges_tuple  # noqa: E501
        assert db.get_used_query_range(cursor, 'poloniex_asset_movements_poloniex') is None
        assert db.get_used_query_range(cursor, 'uniswap_trades') == expected_ranges_tuple

        # load from the database the updated history events
        cursor.execute(
            f'SELECT {HISTORY_BASE_ENTRY_FIELDS} FROM history_events WHERE identifier=?',
            (test_event_id,),
        )
        updated_event = HistoryEvent.deserialize_from_db(cursor.fetchall()[0][1:])
        # the location label should have been already updated
        assert updated_event.location_label == kraken.name
        # update the expected id and location label in the local object and check that no other
        # information has changed
        test_event.location_label = kraken.name
        test_event.identifier = test_event_id
        assert test_event == updated_event

    # Make sure that existing location exchange but wrong name returns error
    data = {'name': 'some_poloniex', 'location': 'poloniex', 'new_name': 'other_poloniex'}
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Could not find poloniex exchange some_poloniex for editing',
    )
    # Make sure that real location but not registered returns error
    data = {'name': 'kucoin', 'location': 'kucoin', 'new_name': 'other_kucoin'}
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Could not find kucoin exchange kucoin for editing',
    )
    # Make sure that not existing location returns error
    data = {'name': 'kucoin', 'location': 'fakeexchange', 'new_name': 'other_kucoin'}
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Failed to deserialize Location value fakeexchange',
    )


@pytest.mark.parametrize('added_exchanges', [(Location.COINBASEPRO, Location.KUCOIN)])
def test_edit_exchange_account_passphrase(rotkehlchen_api_server_with_exchanges):
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    coinbasepro = try_get_first_exchange(rotki.exchange_manager, Location.COINBASEPRO)
    kucoin = try_get_first_exchange(rotki.exchange_manager, Location.KUCOIN)
    assert kucoin.name == 'kucoin'
    assert kucoin.api_passphrase == '123'
    assert coinbasepro.name == 'coinbasepro'
    assert coinbasepro.session.headers['CB-ACCESS-PASSPHRASE'] == '123'

    # change both passphrase and name -- kucoin
    data = {'name': 'kucoin', 'location': 'kucoin', 'new_name': 'my_kucoin', 'passphrase': '$123$'}
    with mock_validate_api_key_success(Location.KUCOIN):
        response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_response_with_result(response)
    assert result is True
    kucoin = try_get_first_exchange(rotki.exchange_manager, Location.KUCOIN)
    assert kucoin.name == 'my_kucoin'
    assert kucoin.api_passphrase == '$123$'

    # change only passphrase -- coinbasepro
    data = {'name': 'coinbasepro', 'location': 'coinbasepro', 'passphrase': '$321$'}
    with mock_validate_api_key_success(Location.COINBASEPRO):
        response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_response_with_result(response)
    assert result is True
    coinbasepro = try_get_first_exchange(rotki.exchange_manager, Location.COINBASEPRO)
    assert coinbasepro.name == 'coinbasepro'
    assert coinbasepro.session.headers['CB-ACCESS-PASSPHRASE'] == '$321$'


@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
def test_edit_exchange_kraken_account_type(rotkehlchen_api_server_with_exchanges):
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    kraken = try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN)
    assert kraken.account_type == DEFAULT_KRAKEN_ACCOUNT_TYPE
    assert kraken.call_limit == 15
    assert kraken.reduction_every_secs == 3

    data = {'name': 'mockkraken', 'location': 'kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'intermediate'}
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_response_with_result(response)
    assert result is True
    kraken = try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN)
    assert kraken.name == 'mockkraken'
    assert kraken.account_type == KrakenAccountType.INTERMEDIATE
    assert kraken.call_limit == 20
    assert kraken.reduction_every_secs == 2

    # at second edit, also change name
    data = {'name': 'mockkraken', 'new_name': 'lolkraken', 'location': 'kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'pro'}  # noqa: E501
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_response_with_result(response)
    assert result is True
    kraken = try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN)
    assert kraken.name == 'lolkraken'
    assert kraken.account_type == KrakenAccountType.PRO
    assert kraken.call_limit == 20
    assert kraken.reduction_every_secs == 1

    # Make sure invalid type is caught
    data = {'name': 'lolkraken', 'location': 'kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'pleb'}
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Failed to deserialize KrakenAccountType value pleb',
    )


@pytest.mark.parametrize('added_exchanges', [SUPPORTED_EXCHANGES])
def test_edit_exchange_credentials(rotkehlchen_api_server_with_exchanges):
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen

    # Test that valid api key/secret is edited properly
    new_key = 'new_key'
    new_secret = 'new_secret'
    for location in SUPPORTED_EXCHANGES:
        exchange = try_get_first_exchange(rotki.exchange_manager, location)
        # change both passphrase and name -- kucoin
        data = {
            'name': exchange.name,
            'location': str(location),
            'new_name': f'my_{exchange.name}',
            'api_key': new_key,
            'api_secret': new_secret,
        }
        if location in (Location.BINANCE, Location.BINANCEUS):
            data['binance_markets'] = ['ETHBTC']
        elif location == Location.KRAKEN:
            data['kraken_account_type'] = KrakenAccountType.STARTER.serialize()
        with mock_validate_api_key_success(location):
            response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
            assert_simple_ok_response(response)
            assert exchange.api_key == new_key
            assert exchange.secret == new_secret.encode()
            if location == Location.ICONOMI:
                continue  # except for iconomi
            # all of the api keys end up in session headers. Check they are properly
            # updated there
            assert any(new_key in value for _, value in exchange.session.headers.items())

    # Test that api key validation failure is handled correctly
    for location in SUPPORTED_EXCHANGES:
        exchange = try_get_first_exchange(rotki.exchange_manager, location)
        # change both passphrase and name -- kucoin
        data = {
            'name': exchange.name,
            'location': str(location),
            'new_name': f'my_{exchange.name}',
            'api_key': 'invalid',
            'api_secret': 'invalid',
        }
        with mock_validate_api_key_failure(location):
            response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
            assert_error_response(
                response=response,
                contained_in_msg='BOOM ERROR',
                status_code=HTTPStatus.CONFLICT,
            )
            # Test that the api key/secret DID NOT change
            assert exchange.api_key == new_key
            assert exchange.secret == new_secret.encode()
            if location == Location.ICONOMI:
                continue  # except for iconomi
            # all of the api keys end up in session headers. Check they are properly
            # updated there
            assert any(new_key in value for _, value in exchange.session.headers.items())


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE,)])
def test_binance_query_pairs(rotkehlchen_api_server_with_exchanges):
    """Test that the binance endpoint returns some market pairs"""
    ci_run = 'CI' in os.environ
    server = rotkehlchen_api_server_with_exchanges
    binance_globaldb = GlobalDBBinance(GlobalDBHandler())
    if ci_run is False:
        response = requests.get(
            api_url_for(
                server,
                'binanceavailablemarkets',
            ),
            params={'location': Location.BINANCE},
        )
        result = assert_proper_response_with_result(response)
        some_pairs = {'ETHUSDC', 'BTCUSDC', 'BNBBTC', 'FTTBNB'}
        assert some_pairs.issubset(result)
        binance_pairs_num = len(binance_globaldb.get_all_binance_pairs(Location.BINANCE))
        assert binance_pairs_num != 0

    response = requests.get(
        api_url_for(
            server,
            'binanceavailablemarkets',
        ),
        params={'location': Location.BINANCEUS},
    )
    binanceus_pairs_num = len(binance_globaldb.get_all_binance_pairs(Location.BINANCEUS))
    assert binanceus_pairs_num != 0
    result = assert_proper_response_with_result(response)
    some_pairs = {'ETHUSD', 'BTCUSDC', 'BNBUSDT'}
    assert some_pairs.issubset(result)
    assert 'FTTBNB' not in result
    if ci_run is False:
        assert binance_pairs_num > binanceus_pairs_num


@pytest.mark.parametrize('default_mock_price_value', [FVal('5.5')])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE,)])
def test_get_binance_savings_balance(rotkehlchen_api_server_with_exchanges):
    """Check that querying the binance savings balance endpoint returns the expected response."""
    async_query = random.choice([True, False])

    # check for errors
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'binancesavingsresource',
            location=Location.KRAKEN.name.lower(),
        ),
    )
    assert_error_response(response, 'is not one of binance,binanceus')
    test_vars = {
        'interest_daily_call_count': 0,
        'interest_customized_fixed_call_count': 0,
        'interest_activity_call_count': 0,
        'ranges_queried': set(),
    }

    def mock_api_query(api_type, method, options):
        return mock_api_query_for_binance_lending(
            api_type=api_type,
            method=method,
            options=options,
            test_vars=test_vars,
        )

    with patch('rotkehlchen.exchanges.binance.Binance.api_query', side_effect=mock_api_query):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'binancesavingsresource',
                location=Location.BINANCE.name.lower(),
            ),
            json={'async_query': async_query},
        )
        if async_query is True:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(rotkehlchen_api_server_with_exchanges, task_id)  # noqa: E501
        else:
            result = assert_proper_response_with_result(response)

        test_vars.pop('ranges_queried')
        for key, value in test_vars.items():
            if key == 'interest_daily_call_count':
                assert value == 2
            else:
                assert value == 1

        events = result.pop('entries')
        assert len(events) == 4
        assert result == {
            'entries_found': 4,
            'entries_limit': 100,
            'entries_total': 4,
            'total_usd_value': '0.09284682',
            'assets': [A_USDT.identifier, A_BUSD.identifier, A_DAI.identifier],
            'received': [
                {
                    'asset': A_BUSD.identifier,
                    'amount': '0.00012816',
                    'usd_value': '0.00070488',
                },
                {
                    'asset': A_DAI.identifier,
                    'amount': '0.00987654',
                    'usd_value': '0.05432097',
                },
                {
                    'asset': A_USDT.identifier,
                    'amount': '0.00687654',
                    'usd_value': '0.03782097',
                },
            ],
        }
