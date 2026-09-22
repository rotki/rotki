import os
import random
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import _patch, patch

import pytest
import requests

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.connections.types import ConnectionRangeKind, connection_range_name
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDT
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import BINANCE_HISTORY_START_TS_KEY, KRAKEN_ACCOUNT_TYPE_KEY
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import HISTORY_BASE_ENTRY_FIELDS, DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.binance import Binance
from rotkehlchen.exchanges.bitfinex import API_KEY_ERROR_MESSAGE as BITFINEX_API_KEY_ERROR_MESSAGE
from rotkehlchen.exchanges.bitstamp import (
    API_KEY_ERROR_CODE_ACTION as BITSTAMP_API_KEY_ERROR_CODE_ACTION,
)
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.exchanges.constants import (
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    SUPPORTED_EXCHANGES,
)
from rotkehlchen.exchanges.data_structures import BinancePair
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.kraken import DEFAULT_KRAKEN_ACCOUNT_TYPE, Kraken, KrakenAccountType
from rotkehlchen.exchanges.kucoin import (
    API_KEY_ERROR_CODE_ACTION as KUCOIN_API_KEY_ERROR_CODE,
    Kucoin,
)
from rotkehlchen.exchanges.okx import Okx, OkxLocation
from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.binance import GlobalDBBinance
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_BINANCEUS,
    LOCATION_BITPANDA,
    LOCATION_COINBASE,
    LOCATION_CRYPTOCOM,
    LOCATION_HTX,
    LOCATION_ICONOMI,
    LOCATION_KRAKEN,
    LOCATION_KUCOIN,
    LOCATION_OKX,
    LOCATION_POLONIEX,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.exchanges import (
    assert_binance_balances_result,
    assert_poloniex_balances_result,
    patch_binance_balances_query,
    patch_poloniex_balances_query,
    try_get_first_exchange,
)
from rotkehlchen.tests.utils.factories import make_random_uppercasenumeric_string
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.tests.fixtures import WebsocketReader


def mock_validate_api_key() -> None:
    raise ValueError('BOOM ERROR!')


def _listed(response: requests.Response) -> list[dict[str, Any]]:
    """The connected exchanges without their generated identifiers"""
    return [
        {k: v for k, v in entry.items() if k != 'identifier'}
        for entry in assert_proper_sync_response_with_result(response)
    ]


def _connection_id(server: APIServer, connector: str, name: str) -> str:
    exchange = server.rest_api.rotkehlchen.exchange_manager.get_exchange_by_name(connector, name)
    assert exchange is not None
    return exchange.connection_identifier


def _assert_connection_created(response: requests.Response) -> str:
    return assert_proper_sync_response_with_result(response)['identifier']


API_KEYPAIR_KRAKEN_VALIDATION_FAIL_PATCH = patch(
    'rotkehlchen.exchanges.kraken.Kraken.validate_api_key',
    side_effect=mock_validate_api_key,
)


def mock_validate_api_key_success(location: LocationIdentifier) -> _patch:
    name = str(location)
    if location == LOCATION_BINANCEUS:
        name = 'binance'
    return patch(
        f'rotkehlchen.exchanges.{name}.{name.capitalize()}.validate_api_key',
        return_value=(True, ''),
    )


def mock_validate_api_key_failure(location: LocationIdentifier) -> _patch:
    name = str(location)
    if location == LOCATION_BINANCEUS:
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
def test_setup_exchange(rotkehlchen_api_server: APIServer) -> None:
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
            'connector': str(location),
            'name': f'my_{location!s}',
            'api_key': api_key,
        }
        if location not in EXCHANGES_WITHOUT_API_SECRET:
            data['api_secret'] = api_secret
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
                'CoinEx request at',
                '',  # poloniex fails with no error message now
            ],
            status_code=HTTPStatus.CONFLICT,
        )
    # Make sure that no exchange is registered after that
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert len(rotki.exchange_manager.connected_exchanges) == 0

    # Mock the api pair validation and make sure that the exchange is setup
    data = {'connector': 'kraken', 'name': 'my_kraken', 'api_key': api_key, 'api_secret': api_secret}  # noqa: E501
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    kraken_id = _assert_connection_created(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert assert_proper_sync_response_with_result(response) == [{'identifier': kraken_id, 'connector': 'kraken', 'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'}]  # noqa: E501

    # Check that we get an error if we try to re-setup an already setup exchange
    data = {'connector': 'kraken', 'name': 'my_kraken', 'api_key': api_key, 'api_secret': api_secret}  # noqa: E501
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        contained_in_msg='kraken exchange my_kraken is already registered',
        status_code=HTTPStatus.CONFLICT,
    )

    # But check that same location different name works
    data = {'connector': 'kraken', 'name': 'my_other_kraken', 'api_key': 'aadddddd', 'api_secret': 'ZmZmZmZmZg=='}  # noqa: E501
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert _assert_connection_created(response) != kraken_id

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert _listed(response) == [
        {'connector': 'kraken', 'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},  # noqa: E501
        {'connector': 'kraken', 'location': 'kraken', 'name': 'my_other_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},  # noqa: E501
    ]

    # Check that giving a passphrase is fine
    data = {'connector': 'kucoin', 'name': 'my_kucoin', 'api_key': api_key, 'api_secret': api_secret, 'passphrase': 'sdf'}  # noqa: E501
    with mock_validate_api_key_success(LOCATION_KUCOIN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    _assert_connection_created(response)
    # and check that kucoin is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert _listed(response) == [
        {'connector': 'kraken', 'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},  # noqa: E501
        {'connector': 'kraken', 'location': 'kraken', 'name': 'my_other_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'},  # noqa: E501
        {'connector': 'kucoin', 'location': 'kucoin', 'name': 'my_kucoin'},
    ]


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(LOCATION_KRAKEN,)])
def test_kraken_malformed_response(rotkehlchen_api_server_with_exchanges: APIServer) -> None:
    """Test that if rotki gets a malformed response from Kraken it's handled properly

    Regression test for the first part of https://github.com/rotki/rotki/issues/943
    and for https://github.com/rotki/rotki/issues/946
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    kraken = try_get_first_exchange(rotki.exchange_manager, LOCATION_KRAKEN, Kraken)
    assert isinstance(kraken, MockKraken)
    kraken.cache_ttl_secs = 0
    kraken.use_original_kraken = True
    response_data = '{"'

    def mock_kraken_return(url: str, *args: Any, **kwargs: Any) -> MockResponse:  # pylint: disable=unused-argument
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
    result = assert_proper_sync_response_with_result(response=response)
    assert result == {}


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_setup_exchange_does_not_stay_in_mapping_after_500_error(
        rotkehlchen_api_server: APIServer,
) -> None:
    """Test that if 500 error is returned during setup of an exchange and it's stuck
    in the exchange mapping rotki doesn't still think the exchange is registered.

    Regression test for the second part of https://github.com/rotki/rotki/issues/943
    """
    data = {'connector': 'kraken', 'name': 'my_kraken', 'api_key': 'ddddd', 'api_secret': 'ZmZmZmZmZg=='}  # noqa: E501
    with API_KEYPAIR_KRAKEN_VALIDATION_FAIL_PATCH:
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
    )

    # Now try to register the exchange again
    data = {'connector': 'kraken', 'name': 'my_kraken', 'api_key': 'ddddd', 'api_secret': 'ZmZmZmZmZg=='}  # noqa: E501
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    _assert_connection_created(response)

    # and check that kraken is now registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert _listed(response) == [{'connector': 'kraken', 'location': 'kraken', 'name': 'my_kraken', KRAKEN_ACCOUNT_TYPE_KEY: 'starter'}]  # noqa: E501


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_setup_exchange_errors(rotkehlchen_api_server: APIServer) -> None:
    """Test errors and edge cases of setup_exchange endpoint"""

    # Provide unsupported exchange location
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'connector': 'notexisting', 'name': 'foo', 'api_key': 'ddddd', 'api_secret': 'ZmZmZmZmZg=='},  # noqa: E501
        )
    assert_error_response(
        response=response,
        contained_in_msg='notexisting is not a supported exchange',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type exchange location
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'connector': 3434, 'name': 'foo', 'api_key': 'ddddd', 'api_secret': 'ZmZmZmZmZg=='},  # noqa: E501
        )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Provide invalid type exchange name
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'connector': 'kraken', 'name': 55, 'api_key': 'ddddd', 'api_secret': 'ZmZmZmZmZg=='},  # noqa: E501
        )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit exchange name and location
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'api_key': 'ddddd', 'api_secret': 'ZmZmZmZmZg=='},
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'exchangesresource'),
        json={
            'api_key': 'ddddd',
            'api_secret': 'ZmZmZmZmZg==',
            'binance_history_start_ts': ts_now() + 60,
            'binance_markets': ['BTCUSDT'],
            'connector': 'binance',
            'name': 'binance',
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='must not be in the future',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Provide invalid type for api key
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'name': 'kraken', 'api_key': True, 'api_secret': 'ZmZmZmZmZg=='},
        )
    assert_error_response(
        response=response,
        contained_in_msg='Given API Key should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api key
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'name': 'kraken', 'api_secret': 'ZmZmZmZmZg=='},
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Provide invalid type for api secret
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'name': 'kraken', 'api_key': 'ddddd', 'api_secret': 234.1},
        )
    assert_error_response(
        response=response,
        contained_in_msg='Given API Secret should be a string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Omit api secret
    with mock_validate_api_key_success(LOCATION_KRAKEN):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={'name': 'kraken', 'api_key': 'ddddd'},
        )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_binance_history_start_timestamp(rotkehlchen_api_server: APIServer) -> None:
    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with (
        patch.object(
            database,
            'get_latest_binance_csv_import_timestamp',
            return_value=Timestamp(1700000000),
        ),
        patch('rotkehlchen.api.services.exchanges.ts_now', return_value=Timestamp(1800000000)),
    ):
        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'binancehistorystarttimestampresource'),
        )

    assert assert_proper_response_with_result(
        response,
        rotkehlchen_api_server,
    ) == 1700000000


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('location', [LOCATION_BINANCE, LOCATION_BINANCEUS])
def test_setup_binance_with_custom_history_start(
        rotkehlchen_api_server: APIServer,
        location: LocationIdentifier,
) -> None:
    with mock_validate_api_key_success(location):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'),
            json={
                'api_key': 'api_key',
                'api_secret': 'api_secret',
                'binance_history_start_ts': 1700000000,
                'binance_markets': ['BTCUSDT'],
                'connector': location,
                'name': 'my_binance',
            },
        )
    identifier = _assert_connection_created(response)

    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with database.conn.read_ctx() as cursor:
        assert database.get_used_query_range(
            cursor,
            connection_range_name(identifier, 'history_events'),
        ) == (Timestamp(0), Timestamp(1699999999))
    assert database.get_exchange_credentials_extras(identifier)[BINANCE_HISTORY_START_TS_KEY] == Timestamp(1700000000)  # noqa: E501
    assert cast(
        'Binance',
        rotkehlchen_api_server.rest_api.rotkehlchen.exchange_manager.get_exchange(identifier),
    ).history_start_ts == Timestamp(1700000000)


def test_binance_api_without_markets_error(rotkehlchen_api_server: APIServer) -> None:
    """Test that adding Binance API key without markets returns a proper error message"""
    auth_data = {
        'connector': 'binance',
        'name': 'my_binance',
        'api_key': 'test_key',
        'api_secret': 'dGVzdF9zZWNyZXQ=',
    }
    # Test Binance without markets
    with mock_validate_api_key_success(LOCATION_BINANCE):
        response = requests.put(
            (endpoint := api_url_for(rotkehlchen_api_server, 'exchangesresource')),
            json=auth_data,
        )

    # Check that we get the expected error message
    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert 'message' in data
    # The error message should be flat, not nested JSON
    expected_msg = 'Binance API key requires at least one market pair to be selected. Please choose the trading pairs you want to monitor before adding the API key.'  # noqa: E501
    assert expected_msg in data['message']

    # Test BinanceUS without markets (same requirement)
    with mock_validate_api_key_success(LOCATION_BINANCEUS):
        response = requests.put(endpoint, json=auth_data)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert 'message' in data
    assert expected_msg in data['message']

    # Test that providing empty markets list also triggers the error
    with mock_validate_api_key_success(LOCATION_BINANCE):
        response = requests.put(endpoint, json=auth_data | {'binance_markets': []})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert 'message' in data
    assert expected_msg in data['message']

    # Test that providing markets works correctly
    with mock_validate_api_key_success(LOCATION_BINANCE):
        response = requests.put(
            endpoint,
            json=auth_data | {'binance_markets': ['BTCUSDT', 'ETHUSDT']},
        )

    _assert_connection_created(response)


def test_kraken_futures_only_one_key(rotkehlchen_api_server: APIServer) -> None:
    """
    Test that adding or editing only one of the 2 required
    API keys for Kraken Futures returns error
    """
    endpoint = api_url_for(rotkehlchen_api_server, 'exchangesresource')
    expected_msg = 'Both the Kraken Futures API Key and Secret must be provided.'
    setup_data: dict[str, Any] = {
        'connector': 'kraken',
        'name': 'my_kraken',
        'api_key': 'test_key',
        'api_secret': 'dGVzdF9zZWNyZXQ=',
    }
    identifier = None
    for requests_func in (requests.put, requests.patch):
        for only_one in ({'kraken_futures_api_key': 'test_futures_key'}, {'kraken_futures_api_secret': 'dGVzdF9zZWNyZXQ='}):  # noqa: E501
            with mock_validate_api_key_success(LOCATION_KRAKEN):
                response = requests_func(endpoint, json=setup_data | only_one)
            assert response.status_code == HTTPStatus.BAD_REQUEST
            # The error message should be flat, not nested JSON
            assert expected_msg in response.json()['message']

        # providing both kraken_futures_api_key and kraken_futures_api_secret succeeds
        with mock_validate_api_key_success(LOCATION_KRAKEN):
            response = requests_func(
                endpoint,
                json=setup_data | {'kraken_futures_api_key': 'test_futures_key', 'kraken_futures_api_secret': 'dGVzdF9zZWNyZXQ='},  # noqa: E501
            )
        if identifier is None:
            identifier = _assert_connection_created(response)
            setup_data = {'identifier': identifier}  # edit the connection just set up
        else:
            assert_simple_ok_response(response)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_exchange(rotkehlchen_api_server: APIServer) -> None:
    """Test that removing a setup exchange via the api works"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    # Setup coinbase exchange
    data = {
        'connector': 'coinbase',
        'name': 'Coinbase 1',
        'api_key': 'c11d1dd5-a460-4693-bbb0-9bba8e611e82',
        'api_secret': 'ZmZmZmZmZg==',
    }
    with mock_validate_api_key_success(LOCATION_COINBASE):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    identifier = _assert_connection_created(response)
    # and check it's registered
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert assert_proper_sync_response_with_result(response) == [
        {'identifier': identifier, 'connector': 'coinbase', 'location': 'coinbase', 'name': 'Coinbase 1'},  # noqa: E501
    ]

    # Add query ranges to see that they also get deleted when removing the exchange
    with db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, 0, 1579564096)',  # noqa: E501
            [(connection_range_name(identifier, 'margins'),), (connection_range_name(identifier, 'history_events'),), ('other_connection_history_events',)],  # noqa: E501
        )

    # Now remove the registered coinbase exchange
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json={'identifier': identifier})  # noqa: E501
    assert_simple_ok_response(response)
    # and check that it's not registered anymore
    response = requests.get(api_url_for(rotkehlchen_api_server, 'exchangesresource'))
    assert assert_proper_sync_response_with_result(response) == []
    # Also check that its query ranges have been deleted but not the other ones
    with db.conn.read_ctx() as cursor:
        assert [x[0] for x in cursor.execute('SELECT name from used_query_ranges')] == ['other_connection_history_events']  # noqa: E501

    # now try to remove a non-registered exchange
    response = requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json={'identifier': identifier})  # noqa: E501
    assert_error_response(
        response=response,
        contained_in_msg=f'Exchange connection {identifier} is not registered',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_remove_exchange_errors(rotkehlchen_api_server: APIServer) -> None:
    """Errors and edge cases when using the remove exchange endpoint"""
    for payload, message in (
        ({'identifier': 5533}, 'Not a valid string'),
        ({'identifier': ''}, 'empty'),
        ({}, 'Missing data for required field'),
    ):
        assert_error_response(
            response=requests.delete(api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=payload),  # noqa: E501
            contained_in_msg=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )


@pytest.mark.parametrize('added_exchanges', [(LOCATION_BINANCE, LOCATION_POLONIEX)])
def test_exchange_query_balances(rotkehlchen_api_server_with_exchanges: APIServer) -> None:
    """Test that using the exchange balances query endpoint works fine"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    # query balances of one specific exchange
    server = rotkehlchen_api_server_with_exchanges
    binance = try_get_first_exchange(rotki.exchange_manager, LOCATION_BINANCE, Binance)
    assert binance is not None
    binance_patch = patch_binance_balances_query(binance)
    with binance_patch:
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server_with_exchanges,
            async_query=async_query,
        )
    assert_binance_balances_result(outcome)

    # query balances of all setup exchanges
    poloniex = try_get_first_exchange(rotki.exchange_manager, LOCATION_POLONIEX, Poloniex)
    assert poloniex is not None
    poloniex_patch = patch_poloniex_balances_query(poloniex)
    with binance_patch, poloniex_patch:
        response = requests.get(
            api_url_for(server, 'exchangebalancesresource'),
            json={'async_query': async_query},
        )
        result = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server_with_exchanges,
            async_query=async_query,
        )

    assert_binance_balances_result(result['binance'])
    assert_poloniex_balances_result(result['poloniex'])


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(LOCATION_BINANCE, LOCATION_POLONIEX)])
def test_exchange_query_balances_ignore_cache(
        rotkehlchen_api_server_with_exchanges: APIServer,
) -> None:
    """Test that using the exchange balances query endpoint can ignore cache"""
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    binance = try_get_first_exchange(rotki.exchange_manager, LOCATION_BINANCE, Binance)
    assert binance is not None
    binance_patch = patch_binance_balances_query(binance)
    binance_api_query_dict = patch.object(binance, 'api_query_dict', wraps=binance.api_query_dict)
    binance_api_query_list = patch.object(binance, 'api_query_list', wraps=binance.api_query_list)

    with binance_patch, binance_api_query_dict as bnd, binance_api_query_list as bnl:
        # Query balances for the first time
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ))
        result = assert_proper_sync_response_with_result(response)
        assert_binance_balances_result(result)
        assert bnd.call_count == 2
        assert bnl.call_count == 4
        # Do the query again. Cache should be used.
        binance_patch = patch_binance_balances_query(binance)
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ))
        result = assert_proper_sync_response_with_result(response)
        assert_binance_balances_result(result)
        assert bnd.call_count == 2, 'call count should not have changed. Cache must have been used'
        assert bnl.call_count == 4, 'call count should not have changed. Cache must have been used'
        # Finally do the query and request ignoring of the cache
        binance_patch = patch_binance_balances_query(binance)
        response = requests.get(api_url_for(
            server,
            'named_exchanges_balances_resource',
            location='binance',
        ), json={'ignore_cache': True})
        result = assert_proper_sync_response_with_result(response)
        assert_binance_balances_result(result)
        assert bnd.call_count == 4, 'call count should have changed. Cache should have been ignored'  # noqa: E501
        assert bnl.call_count == 8, 'call count should have changed. Cache should have been ignored'  # noqa: E501


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(LOCATION_BINANCE, LOCATION_POLONIEX)])
def test_exchange_query_balances_errors(
        rotkehlchen_api_server_with_exchanges: APIServer,
) -> None:
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
        contained_in_msg='Given location dasdsad is not one of',
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
def test_delete_external_exchange_data_works(
        rotkehlchen_api_server_with_exchanges: APIServer,
) -> None:
    server = rotkehlchen_api_server_with_exchanges
    rotki = server.rest_api.rotkehlchen

    events = [AssetMovement(
        location=x,
        event_subtype=HistoryEventSubType.RECEIVE,
        timestamp=TimestampMS(0),
        asset=A_BTC,
        amount=FVal(100),
    ) for x in (LOCATION_CRYPTOCOM, LOCATION_KRAKEN)]
    history_db = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.user_write() as write_cursor:
        history_db.add_history_events(write_cursor=write_cursor, history=events)

        assert len(history_db.get_history_events_internal(
            cursor=write_cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )) == 2
    response = requests.delete(
        api_url_for(
            server,
            'named_exchanges_data_resource',
            location='cryptocom',
        ),
    )
    result = assert_proper_sync_response_with_result(response)  # check no validation error happens
    assert result is True
    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(history_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )) == 1


@pytest.mark.parametrize('added_exchanges', [(LOCATION_KRAKEN, LOCATION_POLONIEX)])
def test_edit_exchange_account(rotkehlchen_api_server_with_exchanges: APIServer) -> None:
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    db = rotki.data.db
    event_db = DBHistoryEvents(db)

    kraken = try_get_first_exchange(rotki.exchange_manager, LOCATION_KRAKEN, Kraken)
    poloniex = try_get_first_exchange(rotki.exchange_manager, LOCATION_POLONIEX, Poloniex)
    assert kraken is not None
    assert poloniex is not None
    assert kraken.name == 'mockkraken'
    assert kraken.account_type == DEFAULT_KRAKEN_ACCOUNT_TYPE
    assert poloniex.name == 'poloniex'

    # test event to check that editing an exchange with history events edits the location label
    test_event = HistoryEvent(
        group_identifier='STARK-STARK-STARK',
        sequence_index=0,
        timestamp=TimestampMS(1673146287380),
        location=LOCATION_KRAKEN,
        location_label=kraken.name,
        asset=A_ETH,
        amount=FVal('0.0000400780'),
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        notes='Staking reward from kraken',
    )

    # add some exchanges ranges
    start_ts, end_ts = Timestamp(0), Timestamp(9999)
    with db.user_write() as cursor:
        kinds: tuple[ConnectionRangeKind, ...] = ('margins', 'history_events')
        for exchange in (kraken, poloniex):
            for kind in kinds:
                db.update_used_query_range(cursor, name=connection_range_name(exchange.connection_identifier, kind), start_ts=start_ts, end_ts=end_ts)  # noqa: E501
        test_event_id = event_db.add_history_event(write_cursor=cursor, event=test_event)

    data = {
        'identifier': kraken.connection_identifier,
        'new_name': 'my_kraken',
        'kraken_account_type': KrakenAccountType.STARTER.serialize(),
    }
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_sync_response_with_result(response)
    assert result is True
    assert kraken is not None
    assert kraken.name == 'my_kraken'
    assert kraken.account_type == DEFAULT_KRAKEN_ACCOUNT_TYPE

    # the query ranges are the connection's, so a rename keeps them
    with db.conn.read_ctx() as cursor:
        for exchange in (kraken, poloniex):
            for kind in kinds:
                assert db.get_used_query_range(cursor, connection_range_name(exchange.connection_identifier, kind)) == (start_ts, end_ts)  # noqa: E501

        data = {'identifier': poloniex.connection_identifier, 'new_name': 'my_poloniex'}
        response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
        result = assert_proper_sync_response_with_result(response)
        assert result is True
        poloniex = try_get_first_exchange(rotki.exchange_manager, LOCATION_POLONIEX, Poloniex)
        assert poloniex is not None
        assert poloniex.name == 'my_poloniex'
        assert db.get_used_query_range(cursor, connection_range_name(poloniex.connection_identifier, 'history_events')) == (start_ts, end_ts)  # noqa: E501

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

    # Make sure that an unknown connection returns an error
    data = {'identifier': 'not-a-connection', 'new_name': 'other_poloniex'}
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='Could not find exchange connection not-a-connection for editing',
    )
    # and that renaming onto the name of another connection of the exchange is refused
    with patch.object(rotki.exchange_manager, 'get_exchange_by_name', return_value=kraken):
        response = requests.patch(api_url_for(server, 'exchangesresource'), json={'identifier': kraken.connection_identifier, 'new_name': 'taken'})  # noqa: E501
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='kraken exchange taken is already registered',
    )


@pytest.mark.parametrize('added_exchanges', [(LOCATION_OKX, LOCATION_KUCOIN)])
def test_edit_exchange_account_passphrase(
        rotkehlchen_api_server_with_exchanges: APIServer,
) -> None:
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    okx = try_get_first_exchange(rotki.exchange_manager, LOCATION_OKX, Okx)
    assert okx is not None
    kucoin = try_get_first_exchange(rotki.exchange_manager, LOCATION_KUCOIN, Kucoin)
    assert kucoin is not None
    assert kucoin.name == 'kucoin'
    assert kucoin.api_passphrase == '123'
    assert okx.name == 'okx'
    assert okx.session.headers['OK-ACCESS-PASSPHRASE'] == 'Rotki123!'

    # change both passphrase and name -- kucoin
    data = {'identifier': _connection_id(server, 'kucoin', 'kucoin'), 'new_name': 'my_kucoin', 'passphrase': '$123$'}  # noqa: E501
    with mock_validate_api_key_success(LOCATION_KUCOIN):
        response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_sync_response_with_result(response)
    assert result is True
    kucoin = try_get_first_exchange(rotki.exchange_manager, LOCATION_KUCOIN, Kucoin)
    assert kucoin is not None
    assert kucoin.name == 'my_kucoin'
    assert kucoin.api_passphrase == '$123$'

    # change only passphrase -- okx
    data = {'identifier': _connection_id(server, 'okx', 'okx'), 'passphrase': '$321$'}
    with mock_validate_api_key_success(LOCATION_OKX):
        response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_sync_response_with_result(response)
    assert result is True
    okx = try_get_first_exchange(rotki.exchange_manager, LOCATION_OKX, Okx)
    assert okx is not None
    assert okx.name == 'okx'
    assert okx.session.headers['OK-ACCESS-PASSPHRASE'] == '$321$'


@pytest.mark.parametrize('added_exchanges', [(LOCATION_KRAKEN,)])
def test_edit_exchange_kraken_account_type(
        rotkehlchen_api_server_with_exchanges: APIServer,
) -> None:
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    kraken = try_get_first_exchange(rotki.exchange_manager, LOCATION_KRAKEN, Kraken)
    assert kraken is not None
    assert kraken.account_type == DEFAULT_KRAKEN_ACCOUNT_TYPE
    assert kraken.call_limit == 15
    assert kraken.reduction_every_secs == 3

    data = {'identifier': _connection_id(server, 'kraken', 'mockkraken'), KRAKEN_ACCOUNT_TYPE_KEY: 'intermediate'}  # noqa: E501
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_sync_response_with_result(response)
    assert result is True
    kraken = try_get_first_exchange(rotki.exchange_manager, LOCATION_KRAKEN, Kraken)
    assert kraken is not None
    assert kraken.name == 'mockkraken'
    assert kraken.account_type == KrakenAccountType.INTERMEDIATE
    assert kraken.call_limit == 20
    assert kraken.reduction_every_secs == 2

    # at second edit, also change name
    data = {'identifier': _connection_id(server, 'kraken', 'mockkraken'), 'new_name': 'lolkraken', KRAKEN_ACCOUNT_TYPE_KEY: 'pro'}  # noqa: E501
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    result = assert_proper_sync_response_with_result(response)
    assert result is True
    kraken = try_get_first_exchange(rotki.exchange_manager, LOCATION_KRAKEN, Kraken)
    assert kraken is not None
    assert kraken.name == 'lolkraken'
    assert kraken.account_type == KrakenAccountType.PRO
    assert kraken.call_limit == 20
    assert kraken.reduction_every_secs == 1

    # Make sure invalid type is caught
    data = {'identifier': _connection_id(server, 'kraken', 'lolkraken'), KRAKEN_ACCOUNT_TYPE_KEY: 'pleb'}  # noqa: E501
    response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Failed to deserialize KrakenAccountType value pleb',
    )


@pytest.mark.parametrize('added_exchanges', [SUPPORTED_EXCHANGES])
def test_edit_exchange_credentials(rotkehlchen_api_server_with_exchanges: APIServer) -> None:
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen

    # Test that valid api key/secret is edited properly
    new_key, new_secret, new_secret_kraken = 'new_key', 'new_secret', 'bmV3X3NlY3JldA=='  # last one is base65 for new_secret  # noqa: E501
    for location in SUPPORTED_EXCHANGES:
        assert (exchange := try_get_first_exchange(rotki.exchange_manager, location, ExchangeInterface)) is not None  # noqa: E501
        # change both passphrase and name -- kucoin
        data: dict[str, Any] = {
            'identifier': exchange.connection_identifier,
            'new_name': f'my_{exchange.name}',
            'api_key': new_key,
        }
        if location not in EXCHANGES_WITHOUT_API_SECRET:
            data['api_secret'] = new_secret_kraken if location == LOCATION_KRAKEN else new_secret
        if location in (LOCATION_BINANCE, LOCATION_BINANCEUS):
            data['binance_markets'] = ['ETHBTC']
        elif location == LOCATION_KRAKEN:
            data['kraken_account_type'] = KrakenAccountType.INTERMEDIATE.serialize()
        elif location == LOCATION_OKX:
            data['okx_location'] = OkxLocation.EEA.serialize()

        with (
            mock_validate_api_key_success(location),
            patch('rotkehlchen.exchanges.coinbase.CoinbaseKeyType.detect_type'),
        ):
            response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
            assert_simple_ok_response(response)
            assert exchange.api_key == new_key
            if location not in EXCHANGES_WITHOUT_API_SECRET:
                assert exchange.secret == new_secret.encode()
            if location in (LOCATION_ICONOMI, LOCATION_HTX, LOCATION_CRYPTOCOM, LOCATION_COINBASE):
                continue  # except for these specific exchanges
            # all of the api keys end up in session headers. Check they are properly
            # updated there
            assert any(new_key in value for value in exchange.session.headers.values())

    # Test that api key validation failure is handled correctly
    for location in SUPPORTED_EXCHANGES:
        assert (exchange := try_get_first_exchange(rotki.exchange_manager, location, ExchangeInterface)) is not None  # noqa: E501
        # change both passphrase and name -- kucoin
        data = {
            'identifier': exchange.connection_identifier,
            'new_name': f'my_{exchange.name}',
            'api_key': 'invalid',
            'api_secret': 'aW52YWxpZA==' if location == LOCATION_KRAKEN else 'invalid',  # base64 for 'invalid'  # noqa: E501
        }

        if location in (LOCATION_BINANCE, LOCATION_BINANCEUS):
            data['binance_markets'] = ['ETHBTC']

        with (
            mock_validate_api_key_failure(location),
            patch('rotkehlchen.exchanges.coinbase.CoinbaseKeyType.detect_type'),
        ):
            response = requests.patch(api_url_for(server, 'exchangesresource'), json=data)
            assert_error_response(
                response=response,
                contained_in_msg='BOOM ERROR',
                status_code=HTTPStatus.CONFLICT,
            )
            # Test that the api key/secret DID NOT change
            assert exchange.api_key == new_key
            if location not in EXCHANGES_WITHOUT_API_SECRET:
                assert exchange.secret == new_secret.encode()
            if location in (LOCATION_ICONOMI, LOCATION_HTX, LOCATION_CRYPTOCOM, LOCATION_COINBASE):
                continue  # except for these specific exchanges
            # all of the api keys end up in session headers. Check they are properly
            # updated there
            assert any(new_key in value for value in exchange.session.headers.values())

        with (
            rotki.data.db.conn.read_ctx() as cursor,
            patch('rotkehlchen.exchanges.coinbase.CoinbaseKeyType.detect_type'),
        ):  # reinitialize the exchanges, to see the edited credentials are loaded from the DB
            rotki.exchange_manager.delete_all_exchanges()
            rotki.exchange_manager.initialize_exchanges(
                connections=rotki.data.db.get_exchange_credentials(cursor),
                database=rotki.data.db,
            )
        assert rotki.exchange_manager.connected_exchanges[LOCATION_OKX][0].okx_location == OkxLocation.EEA   # type: ignore  # noqa: E501
        assert rotki.exchange_manager.connected_exchanges[LOCATION_KRAKEN][0].account_type == KrakenAccountType.INTERMEDIATE    # type: ignore  # noqa: E501


@pytest.mark.parametrize('added_exchanges', [(LOCATION_BINANCE,)])
def test_binance_query_pairs(rotkehlchen_api_server_with_exchanges: APIServer) -> None:
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
            params={'location': LOCATION_BINANCE},
        )
        result = assert_proper_sync_response_with_result(response)
        some_pairs = {'ETHUSDC', 'BTCUSDC', 'BNBBTC', 'FTTBNB'}
        assert some_pairs.issubset(result)
        binance_pairs_num = len(binance_globaldb.get_all_binance_pairs(LOCATION_BINANCE))
        assert binance_pairs_num != 0

    response = requests.get(
        api_url_for(
            server,
            'binanceavailablemarkets',
        ),
        params={'location': LOCATION_BINANCEUS},
    )
    binanceus_pairs_num = len(binance_globaldb.get_all_binance_pairs(LOCATION_BINANCEUS))
    assert binanceus_pairs_num != 0
    result = assert_proper_sync_response_with_result(response)
    some_pairs = {'ETHUSD', 'BTCUSDC', 'BNBUSDT'}
    assert some_pairs.issubset(result)
    assert 'FTTBNB' not in result
    if ci_run is False:
        assert binance_pairs_num > binanceus_pairs_num


@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
@pytest.mark.parametrize('added_exchanges', [(LOCATION_BINANCE,)])
def test_query_binance_events(
        rotkehlchen_api_server_with_exchanges: APIServer,
        websocket_connection: WebsocketReader,
) -> None:
    """Test that querying binance events will only query the market pairs set in the db and
    will not try to query all markets if no market pairs are set."""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    binance = cast('Binance', rotki.exchange_manager.get_exchange_by_name(LOCATION_BINANCE, 'binance'))  # noqa: E501
    binance.selected_pairs = []  # create_test_binance automatically selects pairs, so reset this to properly test here.  # noqa: E501

    # Try directly querying with no pairs set to ensure that it never queries all market pairs.
    with (
        pytest.raises(InputError),
        patch.object(binance, 'api_query', side_effect=lambda **kwargs: []) as mock_api_query,
    ):
        binance.query_online_history_events(start_ts=Timestamp(0), end_ts=Timestamp(1600000000))

    websocket_connection.wait_until_messages_num(num=1, timeout=5)
    assert websocket_connection.pop_message() == (missing_ws_msg := {
        'type': str(WSMessageType.BINANCE_PAIRS_MISSING),
        'data': {'location': 'binance', 'name': 'binance'},
    })
    assert len([x for x in mock_api_query.call_args_list if x.kwargs.get('method') == 'myTrades']) == 0  # noqa: E501

    # Query via the API checking the error with no pairs set and that it works when pairs are set.
    for with_pairs in (False, True):
        if with_pairs:
            with rotki.data.db.conn.write_ctx() as write_cursor:
                rotki.data.db.set_binance_pairs(
                    write_cursor=write_cursor,
                    identifier=binance.connection_identifier,
                    pairs=['ETHUSDC', 'ETHBTC', 'BNBBTC'],
                )
            binance.reset_to_db_extras()

        with patch.object(binance, 'api_query', side_effect=lambda **kwargs: []) as mock_api_query:
            response = requests.post(
                api_url_for(rotkehlchen_api_server_with_exchanges, 'exchangeeventsqueryresource'),
                json={'identifier': binance.connection_identifier},
            )
        trades_queries = [x for x in mock_api_query.call_args_list if x.kwargs.get('method') == 'myTrades']  # noqa: E501
        if with_pairs:
            assert_proper_sync_response_with_result(response)
            assert len(trades_queries) == 3
            assert {x.kwargs['options']['symbol'] for x in trades_queries} == {'ETHUSDC', 'ETHBTC', 'BNBBTC'}  # noqa: E501
        else:
            assert_error_response(
                response=response,
                contained_in_msg='Cannot query binance trade history with no market pairs selected.',  # noqa: E501
                status_code=HTTPStatus.CONFLICT,
            )
            websocket_connection.wait_until_messages_num(num=3, timeout=5)
            assert [
               x for x in websocket_connection.messages
               if x['type'] != str(WSMessageType.HISTORY_EVENTS_STATUS)
            ] == [missing_ws_msg]
            assert len(trades_queries) == 0


@pytest.mark.parametrize('added_exchanges', [(LOCATION_KRAKEN,)])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_exchange_events_range_query(
        rotkehlchen_api_server_with_exchanges: APIServer,
        websocket_connection: WebsocketReader,
) -> None:
    """Test that we can ask an exchange for a specific range of events and duplicate
    events are ignored. Also verifies that websocket messages are sent.
    """
    server = rotkehlchen_api_server_with_exchanges
    rotki = server.rest_api.rotkehlchen
    exchange = try_get_first_exchange(rotki.exchange_manager, LOCATION_KRAKEN, Kraken)
    assert exchange is not None

    def make_events() -> list[HistoryEvent]:
        return [
            HistoryEvent(
                group_identifier='evt-1',
                sequence_index=0,
                timestamp=TimestampMS(1),
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=ONE,
            ),
            HistoryEvent(
                group_identifier='evt-2',
                sequence_index=0,
                timestamp=TimestampMS(2),
                location=LOCATION_KRAKEN,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('2'),
            ),
        ]

    with rotki.data.db.conn.read_ctx() as cursor:
        initial_events = cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0]

    with patch.object(exchange, 'query_online_history_events', side_effect=[(make_events(), Timestamp(10))] * 2) as mock_query:  # noqa: E501
        response = requests.post(
            api_url_for(server, 'exchangeeventsrangequeryresource'),
            json=(payload := {
                'identifier': exchange.connection_identifier,
                'from_timestamp': 0,
                'to_timestamp': 100,
            }),
        )
        result = assert_proper_sync_response_with_result(response)
        assert result == {
            'queried_events': 2,
            'stored_events': 2,
            'skipped_events': 0,
            'actual_end_ts': 10,
        }

        response = requests.post(
            api_url_for(server, 'exchangeeventsrangequeryresource'),
            json=payload,
        )
        result = assert_proper_sync_response_with_result(response)
        assert result == {
            'queried_events': 2,
            'stored_events': 0,
            'skipped_events': 2,
            'actual_end_ts': 10,
        }
        # verify that websocket messages are sent during both the range query
        # and the requery of the already queried range
        websocket_connection.wait_until_messages_num(num=6, timeout=2)
        assert [msg['data']['status'] for msg in websocket_connection.messages] == [
            'querying_events_finished',
            'querying_events_status_update',
            'querying_events_started',
        ] * 2

    assert mock_query.call_count == 2
    for call in mock_query.call_args_list:
        start_argument = call.kwargs.get('start_ts', call.args[0] if call.args else None)
        end_argument = call.kwargs.get('end_ts', call.args[1] if len(call.args) > 1 else None)
        assert start_argument == Timestamp(0)
        assert end_argument == Timestamp(100)

    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == initial_events + 2  # noqa: E501


@pytest.mark.parametrize('added_exchanges', [(LOCATION_BINANCE,)])
def test_binance_events_repull_after_deletion(
        rotkehlchen_api_server_with_exchanges: APIServer,
) -> None:
    """Test that re-pulling Binance events after manual deletion restores the deleted events
    by properly bypassing the cache when force_refresh is used.

    This is a regression test for issue https://github.com/rotki/rotki/issues/11032.
    """
    server = rotkehlchen_api_server_with_exchanges
    rotki = server.rest_api.rotkehlchen
    exchange = try_get_first_exchange(rotki.exchange_manager, LOCATION_BINANCE, Binance)
    assert exchange is not None

    # Set up exchange with a test market pair
    test_symbol = 'ETHUSDT'
    exchange.selected_pairs = [test_symbol]
    exchange._symbols_to_pair = {
        test_symbol: BinancePair(
            symbol=test_symbol,
            base_asset=A_ETH.resolve_to_asset_with_oracles(),
            quote_asset=A_USDT.resolve_to_asset_with_oracles(),
            location=LOCATION_BINANCE,
        ),
    }

    def mock_api_trades_response(last_id: int) -> list[dict[str, Any]]:
        if last_id == 0:
            return [{
                'id': 1,
                'symbol': test_symbol,
                'orderId': 1001,
                'orderListId': -1,
                'price': '2000.0',
                'qty': '1.0',
                'quoteQty': '2000.0',
                'commission': '0.001',
                'commissionAsset': 'ETH',
                'time': 1609459200000,  # 2021-01-01
                'isBuyer': True,
                'isMaker': False,
                'isBestMatch': True,
            }, {
                'id': 2,
                'symbol': test_symbol,
                'orderId': 1002,
                'orderListId': -1,
                'price': '2100.0',
                'qty': '0.5',
                'quoteQty': '1050.0',
                'commission': '0.0005',
                'commissionAsset': 'ETH',
                'time': 1609545600000,  # 2021-01-02
                'isBuyer': False,
                'isMaker': True,
                'isBestMatch': True,
            }]
        else:
            return []

    # first query should fetch and store all trades
    with patch.object(exchange, 'api_query_list') as mock_api:
        mock_api.side_effect = lambda api_type, method, options=None: (
            mock_api_trades_response(options.get('fromId', 0))
            if method == 'myTrades'
            else []
        )

        response = requests.post(
            api_url_for(server, 'exchangeeventsqueryresource'),
            json={
                'identifier': exchange.connection_identifier,
            },
        )
        assert assert_proper_sync_response_with_result(response)

    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM history_events WHERE location = ?', (LOCATION_BINANCE,)).fetchone()[0] == (expected_num_of_events := 6)  # noqa: E501
        assert rotki.data.db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.BINANCE_PAIR_LAST_ID,
            connection=exchange.connection_identifier,
            queried_pair=test_symbol,
        ) == 2

    # Delete all Binance events to see the repulling works
    db_history = DBHistoryEvents(rotki.data.db)
    with rotki.data.db.conn.read_ctx() as cursor:
        if len(event_ids := cursor.execute(
            'SELECT identifier FROM history_events WHERE location = ?',
            (LOCATION_BINANCE,),
        ).fetchall()) > 0:
            db_history.delete_history_events_by_identifier([row[0] for row in event_ids])

        assert cursor.execute('SELECT COUNT(*) FROM history_events WHERE location = ?', (LOCATION_BINANCE,)).fetchone()[0] == 0  # noqa: E501

    with patch.object(exchange, 'api_query_list') as mock_api:
        mock_api.side_effect = lambda api_type, method, options=None: (
            mock_api_trades_response(options.get('fromId', 0))
            if method == 'myTrades'
            else []
        )

        response = requests.post(
            api_url_for(server, 'exchangeeventsrangequeryresource'),
            json={
                'identifier': exchange.connection_identifier,
                'from_timestamp': 0,
                'to_timestamp': 1640000000,
            },
        )
        result = assert_proper_sync_response_with_result(response)
        assert result['queried_events'] == expected_num_of_events
        assert result['stored_events'] == expected_num_of_events  # Events should be re-stored
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM history_events WHERE location = ?', (LOCATION_BINANCE,)).fetchone()[0] == expected_num_of_events  # noqa: E501
            assert rotki.data.db.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.BINANCE_PAIR_LAST_ID,
                connection=exchange.connection_identifier,
                queried_pair=test_symbol,
            ) == 2  # Should still be 2, not updated due to force_refresh


@pytest.mark.parametrize('added_exchanges', [(LOCATION_COINBASE,)])
def test_coinbase_events_repull_returns_events(
        rotkehlchen_api_server_with_exchanges: APIServer,
) -> None:
    """Test that Coinbase's requery_exchange_history_events returns events
    from _query_transactions.

    This is a regression test for the issue where query_online_history_events was returning
    an empty list instead of the actual events queried.
    """
    server = rotkehlchen_api_server_with_exchanges
    rotki = server.rest_api.rotkehlchen
    exchange = try_get_first_exchange(rotki.exchange_manager, LOCATION_COINBASE, Coinbase)
    assert exchange is not None

    mock_events = [SwapEvent(
        group_identifier='coinbase_test_1',
        timestamp=TimestampMS(1609459200000),
        location=LOCATION_COINBASE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=ONE,
        location_label=exchange.name,
    ), SwapEvent(
        group_identifier='coinbase_test_2',
        timestamp=TimestampMS(1609545600000),
        location=LOCATION_COINBASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('0.5'),
        location_label=exchange.name,
    )]

    with patch.object(exchange, '_query_transactions', return_value=mock_events):
        result = assert_proper_sync_response_with_result(requests.post(
            api_url_for(server, 'exchangeeventsrangequeryresource'),
            json={
                'identifier': exchange.connection_identifier,
                'from_timestamp': 0,
                'to_timestamp': 1640000000,
            },
        ))
        assert result['queried_events'] == 2
        assert result['stored_events'] == 2
        assert result['skipped_events'] == 0
        with rotki.data.db.conn.read_ctx() as cursor:
            assert cursor.execute('SELECT COUNT(*) FROM history_events WHERE location = ?', (LOCATION_COINBASE,)).fetchone()[0] == 2  # noqa: E501


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_setup_bitpanda_exchange(rotkehlchen_api_server: APIServer) -> None:
    """Test that setting up Bitpanda exchange works as expected.

    This is a regression test that verifies Bitpanda can be added
    without providing an API secret.
    https://github.com/rotki/rotki/issues/9586
    """
    data = {
        'connector': str(LOCATION_BITPANDA),
        'name': 'my_bitpanda',
        'api_key': make_random_uppercasenumeric_string(size=10),
    }
    with mock_validate_api_key_success(LOCATION_BITPANDA):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'exchangesresource'), json=data,
        )
    assert_proper_response(response)
